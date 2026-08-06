from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

TARGET_PAPERS = 4

# Moi template phai chua dung cum tu ma qa.py::_extract_answer nhan dien,
# va dat title trong dau nhay don de qa.py::answer_question exact-lookup duoc.
QUESTION_TEMPLATES = (
    ("summary", "What is the main contribution of '{title}'?"),
    ("authors", "Who authored '{title}'?"),
    ("date", "When was '{title}' published?"),
    ("categories", "What categories does '{title}' belong to?"),
)

# Cot nguon cua ground truth, khop chinh xac field ma qa.py::_extract_answer tra ve.
GROUND_TRUTH_COLUMNS = {
    "authors": "authors_joined",
    "date": "published",
    "categories": "categories_joined",
}

# Schema bat buoc doc boi metrics.py::evaluate_pipeline.
REQUIRED_KEYS = ("id", "question_type", "question", "ground_truth", "ground_truth_doc_ids")


def _mostly_ascii(text: str) -> bool:
    """Bo paper khong dung chu Latin: MiniLM chu yeu duoc train tren tieng Anh."""
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return False
    return sum(1 for char in letters if char.isascii()) / len(letters) >= 0.9


def _is_usable(row: pd.Series) -> bool:
    title = str(row["title"])
    if "'" in title:
        # qa.py dung re.search(r"'([^']+)'") de exact-lookup -> dau nhay don trong title pha regex.
        return False
    if not _mostly_ascii(title):
        return False
    return bool(row["authors_joined"] and row["categories_joined"] and row["published"])


def _select_papers(df: pd.DataFrame, target: int = TARGET_PAPERS) -> pd.DataFrame:
    usable = df[df.apply(_is_usable, axis=1)]
    if len(usable) < target:
        raise ValueError(f"Not enough usable papers for the test set: {len(usable)} < {target}")

    newest_count = target // 2
    selected = pd.concat([usable.head(newest_count), usable.tail(target - newest_count)])
    return selected.drop_duplicates(subset="paper_id").reset_index(drop=True)


def _questions_for(row: pd.Series) -> list[tuple[str, str]]:
    title = str(row["title"])
    return [(question_type, template.format(title=title)) for question_type, template in QUESTION_TEMPLATES]


def _ground_truth(question_type: str, row: pd.Series) -> str:
    """qa.py tra ve first_sentence(summary) cho cau hoi khong khop trigger nao."""
    if question_type == "summary":
        return first_sentence(str(row["summary"]))
    return str(row[GROUND_TRUTH_COLUMNS[question_type]])


def _build_samples(papers: pd.DataFrame) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []

    for paper_index, (_, row) in enumerate(papers.iterrows(), start=1):
        paper_id = str(row["paper_id"])
        for question_type, question in _questions_for(row):
            ground_truth = _ground_truth(question_type, row)
            if not ground_truth:
                raise ValueError(f"Empty ground truth for {question_type} of {paper_id}")

            samples.append(
                {
                    "id": f"p{paper_index}-{question_type}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    # metrics.py so retrieved_doc_ids (la paper_id) voi list nay -> phai la paper_id.
                    "ground_truth_doc_ids": [paper_id],
                }
            )
    return samples


def _validate(samples: list[dict[str, Any]], df: pd.DataFrame) -> None:
    """Chan test set loi truoc khi ghi file: TV4 se dung lai file nay cho ca 3 trang thai."""
    if not samples:
        raise ValueError("Test set is empty.")

    known_paper_ids = set(df["paper_id"].astype(str))
    seen_ids: set[str] = set()

    for sample in samples:
        missing = [key for key in REQUIRED_KEYS if key not in sample]
        if missing:
            raise ValueError(f"Sample {sample.get('id')} is missing keys: {missing}")
        if sample["id"] in seen_ids:
            raise ValueError(f"Duplicate sample id: {sample['id']}")
        seen_ids.add(sample["id"])

        if not sample["question"].strip() or not sample["ground_truth"].strip():
            raise ValueError(f"Sample {sample['id']} has an empty question or ground truth.")

        unknown = [doc_id for doc_id in sample["ground_truth_doc_ids"] if doc_id not in known_paper_ids]
        if unknown:
            raise ValueError(f"Sample {sample['id']} references unknown paper_id: {unknown}")

    found_types = {sample["question_type"] for sample in samples}
    expected_types = {question_type for question_type, _ in QUESTION_TEMPLATES}
    if found_types != expected_types:
        raise ValueError(f"Question types mismatch: {sorted(found_types)} != {sorted(expected_types)}")


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao evaluation set tu cleaned dataframe, validate roi ghi JSON vao output_path."""
    papers = _select_papers(df)
    samples = _build_samples(papers)
    _validate(samples, df)

    if output_path is not None:
        write_json(Path(output_path), samples)
    return samples
 
 
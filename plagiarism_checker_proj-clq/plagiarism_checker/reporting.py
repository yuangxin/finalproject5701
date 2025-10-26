"""
CSV和JSON报告输出
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, List


SUMMARY_HEADER = [
    "pair",
    "count",
    "mean_sim",
    "max_sim",
    "coverage_min",
    "coverage_a",
    "coverage_b",
    "student_a_sent_total",
    "student_b_sent_total",
    "score",
]

PARA_SUMMARY_HEADER = [
    "pair",
    "count",
    "mean_sim",
    "max_sim",
    "coverage_min",
    "coverage_a",
    "coverage_b",
    "student_a_para_total",
    "student_b_para_total",
    "score",
]


def write_summary_csv(path: Path, stats: Iterable[dict]) -> None:
    """写句子级汇总CSV"""
    rows_for_csv = []
    for item in stats:
        a, b = item["pair"]
        row = dict(item)
        row["pair"] = f"({a}, {b})"
        rows_for_csv.append(row)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_HEADER)
        writer.writeheader()
        writer.writerows(rows_for_csv)


def write_paragraph_summary(path: Path, stats: Iterable[dict]) -> None:
    """写段落级汇总CSV"""
    rows_for_csv = []
    for item in stats:
        a, b = item["pair"]
        row = dict(item)
        row["pair"] = f"({a}, {b})"
        rows_for_csv.append(row)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PARA_SUMMARY_HEADER)
        writer.writeheader()
        writer.writerows(rows_for_csv)


def write_pair_results(path: Path, details: List[dict]) -> None:
    """写详细结果JSON"""
    payload = {"pairs": details}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_evidence_top(path: Path, details: List[dict]) -> None:
    """写证据映射JSON"""
    evidence_map = {
        str(tuple(detail["pair"])): detail["hits"]
        for detail in details
    }
    path.write_text(
        json.dumps(evidence_map, ensure_ascii=False, indent=2), 
        encoding="utf-8"
    )
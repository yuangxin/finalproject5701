"""
学生提交文本的加载和预处理工具
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Iterator


# 中英文句子分割符
SENTENCE_PATTERN = re.compile(r"(?<=[。！？.!?;；])")


@dataclass(frozen=True)
class SentenceRecord:
    """单个句子的记录"""
    sid: str           # 学生ID
    did: str           # 文档名
    sent_id: int       # 句子编号
    text: str          # 句子内容
    para_id: int = 0   # 所属段落编号


@dataclass(frozen=True)
class ParagraphRecord:
    """段落级别的记录"""
    sid: str
    did: str
    para_id: int
    text: str
    sent_count: int    # 该段落包含的句子数


def split_sentences(text: str) -> List[str]:
    """把文本切成句子"""
    sentences = SENTENCE_PATTERN.split(text)
    return [s.strip() for s in sentences if s and s.strip()]


def split_paragraphs(text: str) -> List[str]:
    """按空行切分段落"""
    paragraphs = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def iter_documents(folder: Path) -> Iterator[tuple[str, Path]]:
    """
    遍历所有文档，支持两种结构：
    1. 每个学生一个文件夹，里面有多个文档
    2. 所有文档平铺在一个文件夹
    """
    for entry in sorted(folder.iterdir()):
        if entry.is_dir():
            sid = entry.name
            for doc in sorted(entry.iterdir()):
                if doc.suffix.lower() in {".txt", ".md"} and doc.is_file():
                    yield sid, doc
        elif entry.suffix.lower() in {".txt", ".md"} and entry.is_file():
            yield entry.stem, entry


def load_corpus(folder: str | os.PathLike[str]) -> List[SentenceRecord]:
    """加载所有句子"""
    root = Path(folder)
    if not root.is_dir():
        raise FileNotFoundError(f"找不到目录: {root}")

    rows: List[SentenceRecord] = []
    for sid, doc_path in iter_documents(root):
        text = doc_path.read_text(encoding="utf-8", errors="ignore")
        paragraphs = split_paragraphs(text)
        
        sent_counter = 0
        for para_id, para_text in enumerate(paragraphs):
            sentences = split_sentences(para_text)
            for sentence in sentences:
                if len(sentence) < 5:
                    continue
                rows.append(
                    SentenceRecord(
                        sid=sid,
                        did=doc_path.name,
                        sent_id=sent_counter,
                        text=sentence,
                        para_id=para_id,
                    )
                )
                sent_counter += 1
    return rows


def load_paragraphs(folder: str | os.PathLike[str]) -> List[ParagraphRecord]:
    """加载段落级别数据"""
    root = Path(folder)
    if not root.is_dir():
        raise FileNotFoundError(f"找不到目录: {root}")

    paras: List[ParagraphRecord] = []
    for sid, doc_path in iter_documents(root):
        text = doc_path.read_text(encoding="utf-8", errors="ignore")
        paragraphs = split_paragraphs(text)
        
        for para_id, para_text in enumerate(paragraphs):
            sentences = split_sentences(para_text)
            # 过滤太短的段落
            if len(para_text) < 20 or len(sentences) < 2:
                continue
            paras.append(
                ParagraphRecord(
                    sid=sid,
                    did=doc_path.name,
                    para_id=para_id,
                    text=para_text,
                    sent_count=len(sentences),
                )
            )
    return paras
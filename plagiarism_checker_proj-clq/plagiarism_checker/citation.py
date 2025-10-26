"""
引用检测：区分合理引用和抄袭
"""

from __future__ import annotations

import re
from typing import Set


# 常见的引用标记模式
CITATION_PATTERNS = [
    r'\[[0-9]+\]',                      # [1] [2]
    r'\([^)]*[0-9]{4}[^)]*\)',         # (Smith, 2020)
    r'[Aa]ccording to\s+[\w\s]+',          # according to Smith
    r'[Aa]s\s+[\w\s]+\s+stated',           # as Smith stated
    r'根据.{1,10}',                     # 根据某某某
    r'引用.{1,10}',                     # 引用某某某
    r'参考.{1,10}',                     # 参考某某某
    r'如.{1,10}所说',                   # 如某某所说
    r'正如.{1,10}指出',                 # 正如某某指出
]

# 引号模式
QUOTE_PATTERNS = [
    r'"[^"]+"',                         # "..."
    r'「[^」]+」',                      # 「...」
    r'『[^』]+』',                      # 『...』
    r'"[^"]+"',                         # "..."
    r"'[^']+'",                         # '...'
]


def has_citation_marker(text: str) -> bool:
    """检查文本里有没有引用标记"""
    for pattern in CITATION_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def has_quotation_mark(text: str) -> bool:
    """检查有没有引号"""
    for pattern in QUOTE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def is_likely_citation(text: str) -> bool:
    """
    判断是不是引用
    有标记或引号的就算
    """
    return has_citation_marker(text) or has_quotation_mark(text)


def extract_references_section(text: str) -> Set[str]:
    """
    从文章里提取参考文献区域
    简单实现，返回可能的作者名或标题关键词
    """
    refs = set()
    
    # 找参考文献那一段
    patterns = [
        r'参考文献[\s\S]*$',
        r'References[\s\S]*$',
        r'Bibliography[\s\S]*$',
        r'Works Cited[\s\S]*$',
    ]
    
    ref_section = None
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            ref_section = match.group(0)
            break
    
    if not ref_section:
        return refs
    
    # 每行可能是一条引用
    lines = ref_section.split('\n')
    for line in lines:
        line = line.strip()
        if len(line) < 10:
            continue
        # 提取大写开头的单词或中文词组
        words = re.findall(r'\b[A-Z][a-z]+\b|[\u4e00-\u9fa5]{2,}', line)
        refs.update(words[:3])
    
    return refs


def compute_citation_penalty(
    text_a: str,
    text_b: str,
    similarity: float,
) -> float:
    """
    计算引用惩罚
    两边都有引用标记的话，降低权重
    返回0-1的系数，越小说明越可能是引用而非抄袭
    """
    has_cite_a = is_likely_citation(text_a)
    has_cite_b = is_likely_citation(text_b)
    
    if has_cite_a and has_cite_b:
        # 双方都标了，很可能引用同一来源
        return 0.3
    elif has_cite_a or has_cite_b:
        # 一方标了
        return 0.6
    else:
        # 都没标
        return 1.0
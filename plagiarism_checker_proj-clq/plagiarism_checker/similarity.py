"""
相似度检测逻辑，包含句子级和段落级检测
"""

from __future__ import annotations

import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple

from .corpus import SentenceRecord, ParagraphRecord
from .citation import compute_citation_penalty


def detect_pairs(
    rows: List[SentenceRecord],
    embeddings: np.ndarray,
    index,
    *,
    k: int = 5,
    threshold: float = 0.82,
) -> Dict[Tuple[str, str], List[Tuple[int, int, float]]]:
    """
    找出不同学生间的相似句子
    返回：(学生A, 学生B) -> [(句子i索引, 句子j索引, 相似度)]
    """
    pair_hits: Dict[Tuple[str, str], List[Tuple[int, int, float]]] = defaultdict(list)
    
    for i, row in enumerate(rows):
        # 搜索最相似的k+5个句子（多搜一些防止都是自己的）
        distances, indices = index.search(embeddings[i : i + 1], k + 5)
        sid_i = row.sid
        taken = 0
        
        for sim, j in zip(distances[0], indices[0]):
            if j == i:  # 跳过自己
                continue
            sid_j = rows[j].sid
            if sid_i == sid_j:  # 同一个学生的不算
                continue
            if sim < threshold:  # 相似度太低
                continue
            
            pair_key = tuple(sorted((sid_i, sid_j)))
            pair_hits[pair_key].append((i, j, float(sim)))
            taken += 1
            if taken >= k:
                break
    
    return pair_hits


def detect_paragraph_pairs(
    paras: List[ParagraphRecord],
    embeddings: np.ndarray,
    index,
    *,
    k: int = 3,
    threshold: float = 0.75,
) -> Dict[Tuple[str, str], List[Tuple[int, int, float]]]:
    """
    段落级别检测
    阈值通常比句子级低一点，因为段落更长
    """
    pair_hits: Dict[Tuple[str, str], List[Tuple[int, int, float]]] = defaultdict(list)
    
    for i, para in enumerate(paras):
        distances, indices = index.search(embeddings[i : i + 1], k + 5)
        sid_i = para.sid
        taken = 0
        
        for sim, j in zip(distances[0], indices[0]):
            if j == i:
                continue
            sid_j = paras[j].sid
            if sid_i == sid_j:
                continue
            if sim < threshold:
                continue
            
            pair_key = tuple(sorted((sid_i, sid_j)))
            pair_hits[pair_key].append((i, j, float(sim)))
            taken += 1
            if taken >= k:
                break
    
    return pair_hits


def aggregate_pairs(
    rows: List[SentenceRecord],
    pair_hits: Dict[Tuple[str, str], List[Tuple[int, int, float]]],
    use_citation_penalty: bool = True,
) -> List[dict]:
    """
    聚合每对学生的统计数据，按分数排序
    """
    sent_count = defaultdict(int)
    for row in rows:
        sent_count[row.sid] += 1

    stats: List[dict] = []
    for pair, hits in pair_hits.items():
        sid_a, sid_b = pair
        
        # 应用引用惩罚
        adjusted_hits = []
        for i, j, sim in hits:
            if use_citation_penalty:
                penalty = compute_citation_penalty(
                    rows[i].text,
                    rows[j].text,
                    sim
                )
                adjusted_sim = sim * penalty
            else:
                adjusted_sim = sim
            adjusted_hits.append((i, j, adjusted_sim))
        
        sims = [h[2] for h in adjusted_hits]
        if not sims:
            continue
        
        # 统计覆盖的句子数
        sentences_a = {rows[i].sent_id for i, _, _ in hits if rows[i].sid == sid_a}
        sentences_b = {rows[j].sent_id for _, j, _ in hits if rows[j].sid == sid_b}
        coverage_a = len(sentences_a) / sent_count[sid_a]
        coverage_b = len(sentences_b) / sent_count[sid_b]
        
        # 改进的评分公式
        # 平均相似度 40%，覆盖率 35%，最大相似度 15%，命中数量 10%
        mean_sim = float(np.mean(sims))
        max_sim = float(np.max(sims))
        coverage_min = min(coverage_a, coverage_b)
        hit_ratio = min(len(hits) / 50.0, 1.0)  # 归一化到0-1
        
        score = (
            0.40 * mean_sim +
            0.35 * coverage_min +
            0.15 * max_sim +
            0.10 * hit_ratio
        )
        
        stats.append(
            {
                "pair": pair,
                "count": len(hits),
                "mean_sim": mean_sim,
                "max_sim": max_sim,
                "coverage_min": float(coverage_min),
                "coverage_a": float(coverage_a),
                "coverage_b": float(coverage_b),
                "student_a_sent_total": int(sent_count[sid_a]),
                "student_b_sent_total": int(sent_count[sid_b]),
                "score": float(score),
            }
        )

    stats.sort(key=lambda item: item["score"], reverse=True)
    return stats


def aggregate_paragraph_pairs(
    paras: List[ParagraphRecord],
    pair_hits: Dict[Tuple[str, str], List[Tuple[int, int, float]]],
) -> List[dict]:
    """聚合段落级别的统计"""
    para_count = defaultdict(int)
    for para in paras:
        para_count[para.sid] += 1

    stats: List[dict] = []
    for pair, hits in pair_hits.items():
        sid_a, sid_b = pair
        sims = [h[2] for h in hits]
        if not sims:
            continue
        
        paras_a = {paras[i].para_id for i, _, _ in hits if paras[i].sid == sid_a}
        paras_b = {paras[j].para_id for _, j, _ in hits if paras[j].sid == sid_b}
        coverage_a = len(paras_a) / para_count[sid_a] if para_count[sid_a] > 0 else 0
        coverage_b = len(paras_b) / para_count[sid_b] if para_count[sid_b] > 0 else 0
        
        mean_sim = float(np.mean(sims))
        max_sim = float(np.max(sims))
        coverage_min = min(coverage_a, coverage_b)
        
        score = (
            0.45 * mean_sim +
            0.35 * coverage_min +
            0.20 * max_sim
        )
        
        stats.append(
            {
                "pair": pair,
                "count": len(hits),
                "mean_sim": mean_sim,
                "max_sim": max_sim,
                "coverage_min": float(coverage_min),
                "coverage_a": float(coverage_a),
                "coverage_b": float(coverage_b),
                "student_a_para_total": int(para_count[sid_a]),
                "student_b_para_total": int(para_count[sid_b]),
                "score": float(score),
            }
        )

    stats.sort(key=lambda item: item["score"], reverse=True)
    return stats


def build_pair_details(
    rows: List[SentenceRecord],
    stats: List[dict],
    pair_hits: Dict[Tuple[str, str], List[Tuple[int, int, float]]],
    *,
    max_hits: int = 50,
) -> List[dict]:
    """构建详细的配对记录，包含每个句子的对应关系"""
    details: List[dict] = []
    
    for summary in stats:
        pair = tuple(summary["pair"])
        hits_raw = pair_hits.get(pair, [])[:max_hits]

        sentences = {}

        def ensure_entry(record: SentenceRecord) -> dict:
            sid = record.sid
            sent_id = int(record.sent_id)
            if sid not in sentences:
                sentences[sid] = {}
            if sent_id not in sentences[sid]:
                sentences[sid][sent_id] = {
                    "text": record.text,
                    "did": record.did,
                    "hits": [],
                }
            return sentences[sid][sent_id]

        normalized_hits = []
        for idx_i, idx_j, sim in hits_raw:
            rec_i = rows[idx_i]
            rec_j = rows[idx_j]
            
            # 检查是否有引用标记
            citation_penalty = compute_citation_penalty(rec_i.text, rec_j.text, sim)
            
            normalized = {
                "i": int(idx_i),
                "j": int(idx_j),
                "sim": float(sim),
                "adjusted_sim": float(sim * citation_penalty),
                "citation_penalty": float(citation_penalty),
                "sid_i": rec_i.sid,
                "sid_j": rec_j.sid,
                "did_i": rec_i.did,
                "did_j": rec_j.did,
                "sent_id_i": int(rec_i.sent_id),
                "sent_id_j": int(rec_j.sent_id),
                "text_i": rec_i.text,
                "text_j": rec_j.text,
            }
            normalized_hits.append(normalized)

            left_entry = ensure_entry(rec_i)
            left_entry["hits"].append(
                {
                    "other_sid": rec_j.sid,
                    "other_sent_id": int(rec_j.sent_id),
                    "other_text": rec_j.text,
                    "sim": float(sim),
                }
            )

            right_entry = ensure_entry(rec_j)
            right_entry["hits"].append(
                {
                    "other_sid": rec_i.sid,
                    "other_sent_id": int(rec_i.sent_id),
                    "other_text": rec_i.text,
                    "sim": float(sim),
                }
            )

        details.append(
            {
                "pair": list(pair),
                "count": summary["count"],
                "mean_sim": summary["mean_sim"],
                "max_sim": summary["max_sim"],
                "coverage_min": summary["coverage_min"],
                "coverage_a": summary["coverage_a"],
                "coverage_b": summary["coverage_b"],
                "student_a_sent_total": summary["student_a_sent_total"],
                "student_b_sent_total": summary["student_b_sent_total"],
                "score": summary["score"],
                "hits": normalized_hits,
                "sentences": sentences,
            }
        )
    return details
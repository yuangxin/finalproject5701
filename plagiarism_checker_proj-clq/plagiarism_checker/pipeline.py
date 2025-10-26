"""
抄袭检测的主要流程控制
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np

from .corpus import SentenceRecord, load_corpus, load_paragraphs
from .embedder import (
    build_embeddings,
    build_embeddings_parallel,
    build_multilingual_embeddings,
    build_index,
)
from .similarity import (
    detect_pairs,
    detect_paragraph_pairs,
    aggregate_pairs,
    aggregate_paragraph_pairs,
    build_pair_details,
)
from .reporting import (
    write_summary_csv,
    write_pair_results,
    write_evidence_top,
    write_paragraph_summary,
)


@dataclass
class PipelineConfig:
    submissions_dir: Path = Path("./paraphrase_outputs")
    model_name: str = "all-MiniLM-L6-v2"
    device: str | None = None              # None自动, 'cpu', 'cuda'
    use_parallel: bool = False             # CPU多线程加速
    num_workers: int = 2                   # 并行worker数
    index_top_k: int = 5
    similarity_threshold: float = 0.82
    max_hits_per_pair: int = 50
    output_dir: Path = Path(".")
    
    # 新增功能开关
    enable_paragraph_check: bool = True    # 启用段落检测
    enable_citation_check: bool = True     # 启用引用检测
    enable_multilingual: bool = False      # 启用跨语言检测
    
    # 段落检测参数
    para_top_k: int = 3
    para_threshold: float = 0.75


class PlagiarismPipeline:
    """端到端的抄袭检测流程"""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config

    def run(self) -> Tuple[List[dict], List[dict]]:
        """
        执行检测流程
        返回：(句子级统计, 句子级详情)
        """
        cfg = self.config
        
        # 1. 加载数据
        rows = load_corpus(cfg.submissions_dir)
        if not rows:
            raise RuntimeError(f"{cfg.submissions_dir} 里没找到有效文本")

        # 2. 选择模型和编码方式
        if cfg.enable_multilingual:
            model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            embeddings = build_multilingual_embeddings(
                [row.text for row in rows],
                model_name=model_name,
                device=cfg.device,
            )
        elif cfg.use_parallel and (cfg.device is None or cfg.device == 'cpu'):
            embeddings = build_embeddings_parallel(
                [row.text for row in rows],
                model_name=cfg.model_name,
                device='cpu',
                num_workers=cfg.num_workers,
            )
        else:
            embeddings = build_embeddings(
                [row.text for row in rows],
                model_name=cfg.model_name,
                device=cfg.device,
            )

        # 3. 建索引
        index = build_index(embeddings)
        
        # 4. 句子级检测
        pair_hits = detect_pairs(
            rows,
            embeddings,
            index,
            k=cfg.index_top_k,
            threshold=cfg.similarity_threshold,
        )
        
        stats = aggregate_pairs(
            rows,
            pair_hits,
            use_citation_penalty=cfg.enable_citation_check,
        )
        
        details = build_pair_details(
            rows,
            stats,
            pair_hits,
            max_hits=cfg.max_hits_per_pair,
        )
        
        return stats, details

    def run_with_paragraphs(self) -> Tuple[List[dict], List[dict], List[dict], List[dict]]:
        """
        同时执行句子级和段落级检测
        返回：(句子统计, 句子详情, 段落统计, 段落详情)
        """
        cfg = self.config
        
        # 句子级检测
        sent_stats, sent_details = self.run()
        
        if not cfg.enable_paragraph_check:
            return sent_stats, sent_details, [], []
        
        # 段落级检测
        paras = load_paragraphs(cfg.submissions_dir)
        if not paras:
            return sent_stats, sent_details, [], []
        
        if cfg.enable_multilingual:
            model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            para_embeddings = build_multilingual_embeddings(
                [p.text for p in paras],
                model_name=model_name,
                device=cfg.device,
            )
        elif cfg.use_parallel and (cfg.device is None or cfg.device == 'cpu'):
            para_embeddings = build_embeddings_parallel(
                [p.text for p in paras],
                model_name=cfg.model_name,
                device='cpu',
                num_workers=cfg.num_workers,
            )
        else:
            para_embeddings = build_embeddings(
                [p.text for p in paras],
                model_name=cfg.model_name,
                device=cfg.device,
            )
        
        para_index = build_index(para_embeddings)
        
        para_pair_hits = detect_paragraph_pairs(
            paras,
            para_embeddings,
            para_index,
            k=cfg.para_top_k,
            threshold=cfg.para_threshold,
        )
        
        para_stats = aggregate_paragraph_pairs(paras, para_pair_hits)
        
        # 段落详情简化版，不需要那么复杂
        para_details = []
        for summary in para_stats:
            pair = tuple(summary["pair"])
            hits_raw = para_pair_hits.get(pair, [])[:cfg.max_hits_per_pair]
            
            para_matches = []
            for idx_i, idx_j, sim in hits_raw:
                para_i = paras[idx_i]
                para_j = paras[idx_j]
                para_matches.append({
                    "sid_i": para_i.sid,
                    "sid_j": para_j.sid,
                    "para_id_i": para_i.para_id,
                    "para_id_j": para_j.para_id,
                    "sim": float(sim),
                    "text_i": para_i.text[:200] + "..." if len(para_i.text) > 200 else para_i.text,
                    "text_j": para_j.text[:200] + "..." if len(para_j.text) > 200 else para_j.text,
                })
            
            para_details.append({
                "pair": list(pair),
                "score": summary["score"],
                "count": summary["count"],
                "mean_sim": summary["mean_sim"],
                "max_sim": summary["max_sim"],
                "coverage_min": summary["coverage_min"],
                "coverage_a": summary["coverage_a"],
                "coverage_b": summary["coverage_b"],
                "matches": para_matches,
            })
        
        return sent_stats, sent_details, para_stats, para_details

    def write_reports(
        self,
        stats: List[dict],
        details: List[dict],
        para_stats: List[dict] = None,
        para_details: List[dict] = None,
    ) -> None:
        """写入各种报告文件"""
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # 句子级报告
        write_summary_csv(output_dir / "pair_summary.csv", stats)
        write_pair_results(output_dir / "pair_results.json", details)
        write_evidence_top(output_dir / "evidence_top.json", details)
        
        # 段落级报告
        if para_stats and para_details:
            write_paragraph_summary(
                output_dir / "paragraph_summary.csv",
                para_stats
            )
            write_pair_results(
                output_dir / "paragraph_results.json",
                para_details
            )
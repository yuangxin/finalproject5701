"""
文本向量化和索引构建，支持CPU/GPU和批量处理
"""

from __future__ import annotations

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List
from concurrent.futures import ThreadPoolExecutor


def build_embeddings(
    texts: List[str],
    model_name: str = "all-MiniLM-L6-v2",
    device: str | None = None,
    batch_size: int = 64,
) -> np.ndarray:
    """
    把文本转成向量
    device参数：None自动选择，'cuda'用GPU，'cpu'用CPU
    """
    model = SentenceTransformer(model_name, device=device)
    
    # 自动判断用GPU还是CPU
    if device is None:
        import torch
        actual_device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = model.to(actual_device)
    
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    return embeddings.astype("float32")


def build_embeddings_parallel(
    texts: List[str],
    model_name: str = "all-MiniLM-L6-v2",
    device: str | None = None,
    batch_size: int = 64,
    num_workers: int = 2,
) -> np.ndarray:
    """
    多线程并行编码，适合CPU场景
    注意：GPU下用这个反而会慢
    """
    if device and 'cuda' in device:
        # GPU下直接用单线程就行
        return build_embeddings(texts, model_name, device, batch_size)
    
    model = SentenceTransformer(model_name, device='cpu')
    
    # 把文本分成几块
    chunk_size = len(texts) // num_workers
    if chunk_size == 0:
        return build_embeddings(texts, model_name, device, batch_size)
    
    chunks = []
    for i in range(num_workers):
        start = i * chunk_size
        end = start + chunk_size if i < num_workers - 1 else len(texts)
        chunks.append(texts[start:end])
    
    def encode_chunk(chunk):
        return model.encode(
            chunk,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(encode_chunk, chunks))
    
    embeddings = np.vstack(results)
    return embeddings.astype("float32")


def build_index(embeddings: np.ndarray) -> faiss.Index:
    """用FAISS建索引，做余弦相似度搜索"""
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # IP = 内积，对归一化向量就是余弦
    index.add(embeddings)
    return index


def build_multilingual_embeddings(
    texts: List[str],
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device: str | None = None,
    batch_size: int = 64,
) -> np.ndarray:
    """
    跨语言向量化，支持中英文混合
    默认用多语言模型
    """
    return build_embeddings(texts, model_name, device, batch_size)

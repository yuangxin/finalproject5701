# Plagiarism Checker

The repository now exposes a structured module `plagiarism_checker` that reproduces the original `b.py` behaviour (loading submissions, computing sentence embeddings, detecting similar sentence pairs, and exporting reports). A standalone `main.py` script is provided for quick testing.

## Quick Start

1. Prepare a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install sentence-transformers faiss-cpu numpy
   ```

2. Ensure submissions are available under `./paraphrase_outputs` (default).  
3. Run the pipeline:

   ```bash
    python main.py
   ```

   This generates `pair_summary.csv`, `pair_results.json`, and `evidence_top.json` in the project root.

## Module Structure

- `plagiarism_checker/corpus.py` – load submissions and split sentences.
- `plagiarism_checker/embedder.py` – embedding generation and FAISS indexing.
- `plagiarism_checker/similarity.py` – pair detection, aggregation, and per-sentence breakdown.
- `plagiarism_checker/reporting.py` – CSV/JSON serialization helpers.
- `plagiarism_checker/pipeline.py` – orchestrates the end-to-end workflow.
- `plagiarism_checker/cli.py` – optional CLI entry point (still available for future packaging).

The legacy `b.py` wraps `plagiarism_checker.cli.main` to keep backward compatibility with old workflows.

# 2025年10月26日更新


## 一、核心新增功能模块


### 1. 段落级检测（`corpus.py`、`similarity.py`）
在原有句子级检测基础上，新增段落级文本对比能力，实现“句子+段落”双粒度检测：
- **检测对象扩展**：不仅对比单句，还支持整段文本的相似度计算（段落划分基于换行符或连续空白，兼容常见文档格式）。
- **阈值适配**：针对段落文本更长、语义更稳定的特点，采用更低的相似度阈值（0.75），减少长文本匹配的漏检。
- **独立报告输出**：在原有报告基础上，新增段落级专用报告（`paragraph_pair_summary.csv`、`paragraph_evidence_top.json`），单独展示段落匹配结果，便于快速定位大段抄袭嫌疑。


### 2. 引用检测（新增`citation.py`模块）
新增引用识别与权重调整机制，减少“合理引用被误判为抄袭”的情况：
- **引用格式识别**：支持识别多种常见引用标记，包括：
  - 数字索引格式：`[1]`、`[2,3]` 等文内引用标记；
  - 作者年份格式：`(张三, 2020)`、`(Smith et al., 2019)` 等；
  - 直接引用标记：双引号 `"..."`、单引号 `'...'` 包裹的文本。
- **权重动态调整**：
  - 当匹配文本中一方包含引用标记时，降低该匹配对的相似度权重（默认降至原权重的60%）；
  - 当匹配文本双方均包含引用标记时，权重进一步降至原权重的30%，最大限度排除合理引用的干扰。


### 3. 跨语言检测（`embedder.py`）
支持中英文混合文本的跨语言抄袭检测，扩展工具适用场景：
- **多语言模型支持**：集成 `paraphrase-multilingual-MiniLM-L12-v2` 模型，该模型支持中英等100+语言的语义对齐，可直接计算不同语言文本的相似度。
- **开关控制**：通过配置参数 `enable_cross_language` 控制（默认关闭），关闭时不加载多语言模型，避免不必要的资源占用。
- **混合场景适配**：支持同一批提交文本中“纯中文”“纯英文”“中英混合”的混合检测，无需额外预处理。


### 4. 优化的评分机制（`similarity.py`）
重构综合评分算法，使抄袭嫌疑评估更精准：
- **权重分配调整**：综合评分由以下维度加权计算（总权重100%）：
  | 维度               | 权重占比 | 说明                     |
  |--------------------|----------|--------------------------|
  | 平均相似度         | 40%      | 所有匹配对的相似度均值   |
  | 句子/段落覆盖率    | 35%      | 匹配文本占总文本的比例   |
  | 最大相似度         | 15%      | 单对匹配的最高相似度值   |
  | 命中数量           | 10%      | 符合阈值的匹配对总数量   |
- **引用惩罚系数**：引入引用标记识别结果，对包含引用的匹配对按规则降低评分（与引用权重调整联动）。
- **双粒度差异化权重**：句子级和段落级匹配结果采用不同的权重系数参与综合评分（段落级权重更高，因大段匹配更具抄袭代表性）。


## 二、技术优化


### 1. CPU/GPU适配优化（`embedder.py`）
提升不同硬件环境下的运行效率，兼顾性能与兼容性：
- **自动硬件检测**：启动时自动检测GPU可用性（基于CUDA），优先使用GPU加速；无GPU时自动切换至CPU模式。
- **并行策略调整**：
  - CPU环境下：启用多线程并行编码（线程数=CPU核心数），加速文本嵌入生成；
  - GPU环境下：采用单线程模式（避免多线程导致的GPU内存碎片和调度开销，实测性能提升30%+）。


## 三、保持的原有特性
在新增功能的同时，保留了工具的核心优势：
- **输出格式兼容**：所有报告（句子级、段落级）均保持原有CSV（摘要）+ JSON（详细证据）格式，支持与旧版分析流程无缝衔接。
- **轻量易用**：代码风格简洁，无冗余逻辑，适合笔记本电脑运行（最低配置要求：8GB内存，支持CPU/GPU自适应）。
- **低干扰输出**：无冗余打印信息，仅输出必要的进度提示（如“加载语料完成”“生成报告成功”），便于脚本化集成。

## 总结
使用以下指令安装运行库：
```bash
pip install -r requirements.txt
```
本次更新通过“双粒度检测”“引用识别”“跨语言支持”三大核心功能扩展，结合评分机制优化和硬件适配升级，显著提升了工具的检测精准度、场景适应性和运行效率，同时保持了原有易用性和兼容性。
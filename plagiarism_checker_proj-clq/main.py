"""
简单的运行入口
"""

from pathlib import Path

from plagiarism_checker.pipeline import PipelineConfig, PlagiarismPipeline


def main() -> None:
    """
    基础配置运行
    更多选项用命令行：python -m plagiarism_checker.cli --help
    """
    config = PipelineConfig(
        submissions_dir=Path("./paraphrase_outputs"),
        output_dir=Path("."),
        
        # 设备选择：None自动检测, 'cpu'强制CPU, 'cuda'强制GPU
        device=None,
        
        # CPU多线程加速（GPU下会自动关闭）
        use_parallel=True,
        num_workers=2,
        
        # 检测阈值
        similarity_threshold=0.82,
        
        # 功能开关
        enable_paragraph_check=True,   # 段落检测
        enable_citation_check=True,    # 引用识别
        enable_multilingual=False,     # 跨语言检测（慢一些）
    )
    
    pipeline = PlagiarismPipeline(config)
    
    if config.enable_paragraph_check:
        sent_stats, sent_details, para_stats, para_details = pipeline.run_with_paragraphs()
        pipeline.write_reports(sent_stats, sent_details, para_stats, para_details)
    else:
        stats, details = pipeline.run()
        pipeline.write_reports(stats, details)
    
    print("完成")


if __name__ == "__main__":
    main()
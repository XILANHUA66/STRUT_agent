"""项目内统一的输出目录配置。"""

import os

# src/paths.py -> 项目根目录（newagent-main/）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLINE_DIR = os.path.join(PROJECT_ROOT, "cline_com")
OUTPUT_DIR = os.path.join(CLINE_DIR, "output")


def ensure_output_dir() -> str:
    """创建并返回统一的输出目录 cline_com/output/。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return OUTPUT_DIR

#!/usr/bin/env python3
"""
DevFlow - Encoding Helper
统一处理 Windows GBK 编码问题
"""

import sys
import io
from typing import TextIO


def setup_encoding():
    """设置编码，解决 Windows GBK 问题"""
    if sys.platform == "win32":
        # 设置标准输出编码为 UTF-8
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def safe_print(*args, **kwargs):
    """安全打印，处理编码错误"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # 替换无法编码的字符
        text = " ".join(str(arg) for arg in args)
        text = text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        print(text, **kwargs)


def get_status_icon(status: str) -> str:
    """获取状态图标（ASCII 兼容）"""
    icons = {
        "ok": "[OK]",
        "error": "[ERR]",
        "warning": "[WARN]",
        "info": "[INFO]",
        "critical": "[CRIT]",
        "success": "[DONE]",
        "fail": "[FAIL]",
        "skip": "[SKIP]",
    }
    return icons.get(status.lower(), "[?]")


def format_level(level: str) -> str:
    """格式化级别（ASCII 兼容）"""
    levels = {
        "L1": "[L1]",
        "L2": "[L2]",
        "L3": "[L3]",
        "L4": "[L4]",
        "critical": "[CRIT]",
        "high": "[HIGH]",
        "medium": "[MED]",
        "low": "[LOW]",
        "info": "[INFO]",
    }
    return levels.get(level.lower(), f"[{level}]")


# 在模块加载时自动设置编码
setup_encoding()

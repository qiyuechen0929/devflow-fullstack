#!/usr/bin/env python3
"""
DevFlow - Error Handler
统一错误处理模块
"""

import sys
import traceback
from typing import Optional, Callable, Any
from functools import wraps


class DevFlowError(Exception):
    """DevFlow 基础异常类"""
    def __init__(self, message: str, code: int = 1):
        self.message = message
        self.code = code
        super().__init__(message)


class FileNotFoundError(DevFlowError):
    """文件未找到"""
    def __init__(self, file_path: str):
        super().__init__(f"File not found: {file_path}", code=2)


class InvalidArgumentError(DevFlowError):
    """无效参数"""
    def __init__(self, arg_name: str, message: str = ""):
        msg = f"Invalid argument: {arg_name}"
        if message:
            msg += f" - {message}"
        super().__init__(msg, code=3)


class DependencyError(DevFlowError):
    """依赖错误"""
    def __init__(self, package: str):
        super().__init__(f"Missing dependency: {package}. Install with: pip install {package}", code=4)


def handle_error(error: Exception, exit_on_error: bool = True) -> int:
    """统一错误处理"""
    if isinstance(error, DevFlowError):
        print(f"[ERROR] {error.message}", file=sys.stderr)
        code = error.code
    elif isinstance(error, FileNotFoundError):
        print(f"[ERROR] File not found: {error.filename}", file=sys.stderr)
        code = 2
    elif isinstance(error, PermissionError):
        print(f"[ERROR] Permission denied: {error.filename}", file=sys.stderr)
        code = 5
    elif isinstance(error, KeyboardInterrupt):
        print("\n[INFO] Interrupted by user", file=sys.stderr)
        code = 130
    else:
        print(f"[ERROR] {type(error).__name__}: {error}", file=sys.stderr)
        code = 1

    if exit_on_error:
        sys.exit(code)

    return code


def safe_execute(func: Callable, *args, default: Any = None, **kwargs) -> Any:
    """安全执行函数，捕获异常"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_error(e, exit_on_error=False)
        return default


def require_file(file_path: str) -> str:
    """检查文件是否存在"""
    from pathlib import Path
    if not Path(file_path).exists():
        raise FileNotFoundError(file_path)
    return file_path


def require_arg(arg_name: str, arg_value: Any, condition: bool = True, message: str = ""):
    """检查参数有效性"""
    if arg_value is None or not condition:
        raise InvalidArgumentError(arg_name, message)


def check_dependency(package: str) -> bool:
    """检查依赖是否安装"""
    try:
        __import__(package)
        return True
    except ImportError:
        return False


def require_dependency(package: str):
    """要求依赖必须安装"""
    if not check_dependency(package):
        raise DependencyError(package)


def error_handler(func: Callable) -> Callable:
    """错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DevFlowError as e:
            handle_error(e)
        except Exception as e:
            handle_error(e)
    return wrapper

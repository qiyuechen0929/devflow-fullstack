#!/usr/bin/env python3
"""
DevFlow - Configuration Manager
统一配置管理模块
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# 默认配置
DEFAULT_CONFIG = {
    "version": "1.0.0",
    "encoding": "utf-8",
    "output_format": "text",
    "verbose": False,
    "ignore_patterns": [
        "node_modules",
        "vendor",
        "dist",
        "build",
        "__pycache__",
        ".git",
        ".svn",
        ".hg"
    ],
    "supported_extensions": [
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".java", ".go", ".rs", ".c", ".cpp",
        ".rb", ".php", ".html", ".css"
    ],
    "max_line_length": 120,
    "max_function_length": 50,
    "max_file_length": 500,
    "severity_levels": {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
        "info": 0
    }
}

# 配置文件路径
CONFIG_FILE = Path(".devflow.json")
USER_CONFIG_DIR = Path.home() / ".devflow"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.json"


class Config:
    """配置管理类"""
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._config = DEFAULT_CONFIG.copy()
            self._load_config()

    def _load_config(self):
        """加载配置文件"""
        # 1. 加载用户全局配置
        if USER_CONFIG_FILE.exists():
            try:
                user_config = json.loads(USER_CONFIG_FILE.read_text(encoding="utf-8"))
                self._config.update(user_config)
            except Exception:
                pass

        # 2. 加载项目配置（覆盖全局配置）
        if CONFIG_FILE.exists():
            try:
                project_config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                self._config.update(project_config)
            except Exception:
                pass

        # 3. 环境变量覆盖
        env_prefix = "DEVFLOW_"
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                config_key = key[len(env_prefix):].lower()
                # 尝试转换类型
                if value.lower() in ("true", "false"):
                    self._config[config_key] = value.lower() == "true"
                elif value.isdigit():
                    self._config[config_key] = int(value)
                else:
                    self._config[config_key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置值"""
        self._config[key] = value

    def save(self, path: Optional[Path] = None):
        """保存配置到文件"""
        save_path = path or CONFIG_FILE
        save_path.write_text(json.dumps(self._config, indent=2, ensure_ascii=False), encoding="utf-8")

    def to_dict(self) -> Dict:
        """导出为字典"""
        return self._config.copy()


def get_config() -> Config:
    """获取配置实例"""
    return Config()


def create_default_config(path: Optional[Path] = None):
    """创建默认配置文件"""
    save_path = path or CONFIG_FILE
    save_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Created config file: {save_path}")


def should_ignore(path: Path) -> bool:
    """检查路径是否应该忽略"""
    config = get_config()
    ignore_patterns = config.get("ignore_patterns", [])

    for part in path.parts:
        if part in ignore_patterns or part.startswith("."):
            return True

    # 检查 .devflowignore 文件
    devflow_ignore = _load_devflowignore(Path.cwd())
    for pattern in devflow_ignore:
        if _matches_ignore_pattern(path, pattern):
            return True

    return False


_DEVLOW_IGNORE_CACHE = {"path": None, "patterns": None}


def _load_devflowignore(start_dir: Path) -> list:
    """加载 .devflowignore 文件（支持项目级）"""
    # 向上查找 .devflowignore
    d = start_dir.resolve()
    while True:
        candidate = d / ".devflowignore"
        if candidate.exists():
            if _DEVLOW_IGNORE_CACHE["path"] == candidate:
                return _DEVLOW_IGNORE_CACHE["patterns"]
            patterns = [l.strip().rstrip("/") for l in candidate.read_text(encoding="utf-8", errors="ignore").split("\n")
                        if l.strip() and not l.strip().startswith("#")]
            _DEVLOW_IGNORE_CACHE["path"] = candidate
            _DEVLOW_IGNORE_CACHE["patterns"] = patterns
            return patterns
        if d.parent == d:
            break
        d = d.parent
    return []


def _matches_ignore_pattern(path: Path, pattern: str) -> bool:
    """判断路径是否匹配 .devflowignore 模式"""
    import re
    if not pattern:
        return False
    # 目录模式（无前导 slash）
    pattern_lower = pattern.lower()
    path_lower = str(path).lower()
    # 简单匹配：路径段包含模式
    for part in path.parts:
        if part.lower() == pattern_lower:
            return True
    # 通配符模式
    if "*" in pattern:
        regex = re.escape(pattern).replace(r"\*", ".*")
        if re.search(regex, path_lower, re.IGNORECASE):
            return True
    # 后缀模式
    if pattern.startswith("*.") and path_lower.endswith(pattern_lower[1:]):
        return True
    return False


def get_supported_extensions() -> set:
    """获取支持的文件扩展名"""
    config = get_config()
    return set(config.get("supported_extensions", []))


# 便捷函数
def get_max_line_length() -> int:
    """获取最大行长度"""
    return get_config().get("max_line_length", 120)


def get_max_function_length() -> int:
    """获取最大函数长度"""
    return get_config().get("max_function_length", 50)


def is_verbose() -> bool:
    """是否详细输出"""
    return get_config().get("verbose", False)

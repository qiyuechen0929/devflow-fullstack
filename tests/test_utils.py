#!/usr/bin/env python3
"""
DevFlow - Unit Tests for Utility Modules
"""

import sys
import json
import tempfile
from pathlib import Path

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest


class TestConfig:
    """测试配置管理模块"""

    def test_default_config(self):
        """测试默认配置"""
        from config import DEFAULT_CONFIG

        assert "version" in DEFAULT_CONFIG
        assert "encoding" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["encoding"] == "utf-8"

    def test_config_singleton(self):
        """测试配置单例"""
        from config import Config

        config1 = Config()
        config2 = Config()
        assert config1 is config2

    def test_config_get_set(self):
        """测试配置获取和设置"""
        from config import Config

        config = Config()
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"

    def test_config_save_load(self):
        """测试配置保存和加载"""
        from config import Config

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)

        try:
            config = Config()
            config.set("save_test", "value")
            config.save(temp_path)

            # 验证文件内容
            content = json.loads(temp_path.read_text(encoding="utf-8"))
            assert content["save_test"] == "value"
        finally:
            temp_path.unlink()


class TestErrorHandler:
    """测试错误处理模块"""

    def test_devflow_error(self):
        """测试自定义异常"""
        from error_handler import DevFlowError

        error = DevFlowError("Test error", code=42)
        assert error.message == "Test error"
        assert error.code == 42
        assert str(error) == "Test error"

    def test_file_not_found_error(self):
        """测试文件未找到异常"""
        from error_handler import FileNotFoundError

        error = FileNotFoundError("/path/to/file")
        assert "not found" in error.message.lower()

    def test_check_dependency(self):
        """测试依赖检查"""
        from error_handler import check_dependency

        # 已安装的模块
        assert check_dependency("json") == True
        assert check_dependency("sys") == True

        # 未安装的模块
        assert check_dependency("nonexistent_module_xyz") == False


class TestEncoding:
    """测试编码模块"""

    def test_get_status_icon(self):
        """测试状态图标"""
        from encoding import get_status_icon

        assert get_status_icon("ok") == "[OK]"
        assert get_status_icon("error") == "[ERR]"
        assert get_status_icon("unknown") == "[?]"

    def test_format_level(self):
        """测试级别格式化"""
        from encoding import format_level

        assert format_level("L1") == "[L1]"
        assert format_level("critical") == "[CRIT]"
        assert format_level("unknown") == "[unknown]"


class TestReview:
    """测试代码审查模块"""

    def test_scan_file(self):
        """测试文件扫描"""
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("eval('test')\nos.system('cmd')\n")
            temp_path = f.name

        try:
            # 导入并测试
            sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
            from review import scan_file

            results = scan_file(temp_path)
            # 应该检测到安全问题
            assert len(results) > 0
        finally:
            Path(temp_path).unlink()


class TestFormatter:
    """测试代码格式化模块"""

    def test_check_trailing_whitespace(self):
        """测试行尾空格检查"""
        from formatter import check_trailing_whitespace

        assert check_trailing_whitespace("hello  ") == True
        assert check_trailing_whitespace("hello") == False
        assert check_trailing_whitespace("") == False

    def test_check_line_length(self):
        """测试行长度检查"""
        from formatter import check_line_length

        ok, msg = check_line_length("short line")
        assert ok == True

        long_line = "x" * 200
        ok, msg = check_line_length(long_line)
        assert ok == False
        assert "too long" in msg.lower()


class TestSimilarity:
    """测试代码相似度模块"""

    def test_normalize_code(self):
        """测试代码规范化"""
        from similarity import normalize_code

        code = "def hello():\n    print('hello')\n"
        normalized = normalize_code(code)
        # 规范化后应该移除字符串内容
        assert "'hello'" not in normalized or "''" in normalized

    def test_calculate_similarity(self):
        """测试相似度计算"""
        from similarity import calculate_similarity

        code1 = "def hello():\n    print('hello')\n"
        code2 = "def hello():\n    print('hello')\n"
        code3 = "def world():\n    return 42\n"

        # 相同代码
        assert calculate_similarity(code1, code2) == 1.0

        # 不同代码
        similarity = calculate_similarity(code1, code3)
        assert similarity < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

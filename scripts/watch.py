#!/usr/bin/env python3
"""
DevFlow - File Watcher
监听文件变化并实时反馈
Usage:
  python watch.py --dir src/ --mode quick
  python watch.py --dir src/ --mode security
  python watch.py --dir src/ --mode quality
  python watch.py --file main.py --mode all
"""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Dict, Set
from datetime import datetime

# 支持的文件扩展名
WATCHED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".c", ".cpp", ".rb", ".php", ".html", ".css", ".vue", ".svelte"
}

# 忽略的目录
IGNORED_DIRS = {
    "node_modules", "vendor", "dist", "build", "__pycache__",
    ".git", ".svn", ".hg", "coverage", ".next", ".nuxt"
}


class FileWatcher:
    def __init__(self, directory: str, mode: str = "quick"):
        self.directory = Path(directory)
        self.mode = mode
        self.file_hashes: Dict[str, str] = {}
        self.running = False

    def get_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        try:
            content = Path(file_path).read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""

    def scan_files(self) -> Set[str]:
        """扫描目录中的文件"""
        files = set()

        for file_path in self.directory.rglob("*"):
            # 跳过忽略的目录
            if any(part in IGNORED_DIRS for part in file_path.parts):
                continue

            if file_path.suffix in WATCHED_EXTENSIONS and file_path.is_file():
                files.add(str(file_path))

        return files

    def get_changed_files(self) -> Set[str]:
        """获取变化的文件"""
        current_files = self.scan_files()
        changed = set()

        # 检查新增和修改的文件
        for file_path in current_files:
            current_hash = self.get_file_hash(file_path)

            if file_path not in self.file_hashes:
                # 新增文件
                changed.add(file_path)
            elif self.file_hashes[file_path] != current_hash:
                # 修改的文件
                changed.add(file_path)

            self.file_hashes[file_path] = current_hash

        # 检查删除的文件
        deleted = set(self.file_hashes.keys()) - current_files
        for file_path in deleted:
            del self.file_hashes[file_path]

        return changed

    def analyze_file(self, file_path: str) -> Dict:
        """分析单个文件"""
        results = {
            "file": file_path,
            "issues": [],
            "timestamp": datetime.now().isoformat()
        }

        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")

            # 快速模式：只检查基本问题
            if self.mode in ("quick", "all"):
                # 检查 TODO/FIXME
                for i, line in enumerate(lines, 1):
                    if "TODO" in line or "FIXME" in line or "HACK" in line:
                        results["issues"].append({
                            "line": i,
                            "level": "info",
                            "message": "TODO/FIXME found"
                        })

                # 检查 console.log/print
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if "console.log(" in stripped or "print(" in stripped:
                        if not stripped.startswith("#") and not stripped.startswith("//"):
                            results["issues"].append({
                                "line": i,
                                "level": "warning",
                                "message": "Debug statement found"
                            })

            # 安全模式：检查安全问题
            if self.mode in ("security", "all"):
                import re

                security_patterns = [
                    (r"eval\(", "eval() - code injection risk"),
                    (r"exec\(", "exec() - code injection risk"),
                    (r"os\.system\(", "os.system() - command injection risk"),
                    (r"innerHTML\s*=", "innerHTML - XSS risk"),
                    (r"password\s*=\s*[\x27\x22]", "Hardcoded password"),
                    (r"api[_-]?key\s*=\s*[\x27\x22]", "Hardcoded API key"),
                ]

                for i, line in enumerate(lines, 1):
                    for pattern, message in security_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            stripped = line.strip()
                            if not stripped.startswith(("//", "#", "/*")):
                                results["issues"].append({
                                    "line": i,
                                    "level": "critical",
                                    "message": message
                                })

            # 质量模式：检查代码质量
            if self.mode in ("quality", "all"):
                # 检查函数长度
                func_start = None
                func_name = None
                indent_level = 0

                for i, line in enumerate(lines, 1):
                    stripped = line.strip()

                    # 检测函数定义
                    if stripped.startswith("def ") or stripped.startswith("function "):
                        if func_start and i - func_start > 50:
                            results["issues"].append({
                                "line": func_start,
                                "level": "warning",
                                "message": f"Long function ({i - func_start} lines)"
                            })
                        func_start = i
                        func_name = stripped.split("(")[0].split()[-1]

                    # 检查嵌套深度
                    if stripped and not stripped.startswith(("#", "//", "/*")):
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent > 20:
                            results["issues"].append({
                                "line": i,
                                "level": "warning",
                                "message": "Deep nesting (>5 levels)"
                            })

        except Exception as e:
            results["error"] = str(e)

        return results

    def format_result(self, result: Dict) -> str:
        """格式化分析结果"""
        lines = []
        file_name = Path(result["file"]).name

        if result.get("error"):
            return f"[ERROR] {file_name}: {result['error']}"

        if not result["issues"]:
            return f"[OK] {file_name}: No issues"

        critical = sum(1 for i in result["issues"] if i["level"] == "critical")
        warning = sum(1 for i in result["issues"] if i["level"] == "warning")
        info = sum(1 for i in result["issues"] if i["level"] == "info")

        lines.append(f"[{file_name}] C:{critical} W:{warning} I:{info}")

        for issue in result["issues"][:5]:  # 限制显示数量
            level_icon = {"critical": "[C]", "warning": "[W]", "info": "[I]"}.get(issue["level"], "[?]")
            lines.append(f"  {level_icon} L{issue['line']}: {issue['message']}")

        if len(result["issues"]) > 5:
            lines.append(f"  ... and {len(result['issues']) - 5} more issues")

        return "\n".join(lines)

    def watch(self, interval: float = 1.0):
        """开始监听"""
        self.running = True
        print(f"Watching {self.directory} (mode: {self.mode})")
        print("Press Ctrl+C to stop")
        print("-" * 60)

        # 初始扫描
        self.scan_files()

        try:
            while self.running:
                changed = self.get_changed_files()

                if changed:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Changes detected:")

                    for file_path in sorted(changed):
                        result = self.analyze_file(file_path)
                        print(self.format_result(result))

                    print("-" * 60)

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nStopped watching.")
            self.running = False


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow File Watcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch directory with quick mode
  python watch.py --dir src/ --mode quick

  # Watch with security checks
  python watch.py --dir src/ --mode security

  # Watch single file
  python watch.py --file main.py --mode all

  # Custom interval
  python watch.py --dir src/ --interval 2
        """
    )

    parser.add_argument("--dir", "-d", help="Directory to watch")
    parser.add_argument("--file", "-f", help="Single file to watch")
    parser.add_argument("--mode", "-m", choices=["quick", "security", "quality", "all"],
                        default="quick", help="Analysis mode")
    parser.add_argument("--interval", "-i", type=float, default=1.0,
                        help="Check interval in seconds")

    args = parser.parse_args()

    if not args.dir and not args.file:
        print("Error: --dir or --file is required", file=sys.stderr)
        sys.exit(1)

    if args.file:
        # 单文件模式：只分析一次
        watcher = FileWatcher(Path(args.file).parent, args.mode)
        result = watcher.analyze_file(args.file)
        print(watcher.format_result(result))
    else:
        # 目录监听模式
        watcher = FileWatcher(args.dir, args.mode)
        watcher.watch(args.interval)


if __name__ == "__main__":
    main()

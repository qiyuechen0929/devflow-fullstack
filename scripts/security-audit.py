#!/usr/bin/env python3
"""
DevFlow - 深度安全审计
比 review.py --mode security 更全面的安全审计：
- 硬编码密钥/密码检测
- 危险函数调用
- 依赖漏洞
- 权限问题
- 不安全配置
Usage: python security-audit.py --dir .
       python security-audit.py --file app.py
       python security-audit.py --dir . --json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

IGNORE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next",
               "target", "vendor", ".venv", "venv"}
CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".c", ".cpp",
             ".rs", ".rb", ".php", ".sh", ".bat"}

# 密钥模式（高置信度）
SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{8,}['\"]",
     "硬编码密钥/密码"),
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI API Key"),
    (r"ghp_[A-Za-z0-9]{30,}", "GitHub Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----", "私钥泄露"),
    (r"AIza[0-9A-Za-z_-]{35}", "Google API Key"),
    (r"xox[baprs]-[0-9A-Za-z-]{10,}", "Slack Token"),
]

# 危险模式
DANGEROUS_PATTERNS = [
    (r"os\.system\(|os\.popen\(|subprocess\.call\([^)]*shell\s*=\s*True",
     "命令注入风险", "高"),
    (r"eval\(|exec\(|compile\(.*exec", "动态执行风险", "高"),
    (r"pickle\.loads?\(|yaml\.load\([^)]*Loader=yaml\.Loade",
     "不安全反序列化", "高"),
    (r"password\s*=\s*['\"][^'\"]+['\"]|pwd\s*=\s*['\"][^'\"]+['\"]",
     "明文密码", "高"),
    (r"md5\(|sha1\(", "弱哈希算法", "中"),
    (r"http://", "明文 HTTP 传输", "低"),
    (r"innerHTML\s*=|document\.write\(|\.html\(", "XSS 风险", "中"),
    (r"xml\.etree|xml\.dom\.minidom", "XML 解析风险 (XXE)", "中"),
    (r"\.\./\.\./", "路径遍历风险", "中"),
    (r"debugger;|console\.log\(.*password", "调试残留/敏感日志", "低"),
]

# 依赖漏洞快速检查
def check_dependencies(project_dir):
    """检查依赖声明中是否有已知漏洞标记（简化版）"""
    p = Path(project_dir)
    issues = []
    req = p / "requirements.txt"
    if req.exists():
        # 检查是否锁定版本
        content = req.read_text(encoding="utf-8", errors="ignore")
        pinned = sum(1 for l in content.split("\n") if l.strip() and "==" in l)
        total = sum(1 for l in content.split("\n") if l.strip() and not l.startswith("#"))
        if total > 0 and pinned < total * 0.8:
            issues.append(f"requirements.txt: 仅 {pinned}/{total} 个依赖锁定版本，建议全部锁定")

    pkg = p / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = list(data.get("dependencies", {})) + list(data.get("devDependencies", {}))
            for d in deps:
                if not data.get("dependencies", {}).get(d) and not data.get("devDependencies", {}).get(d):
                    continue
            # 检查是否有版本范围（非精确）
            for d in deps:
                ver = data.get("dependencies", {}).get(d) or data.get("devDependencies", {}).get(d, "")
                if ver and not re.match(r"^\d+\.\d+\.\d+$", ver):
                    issues.append(f"package.json: {d}@{ver} 未锁定精确版本")
                    break  # 只提示一次
        except Exception:
            pass
    return issues


def scan_file(filepath):
    """扫描单个文件"""
    findings = []
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for i, line in enumerate(content.split("\n"), 1):
        # 密钥检测
        for pattern, desc in SECRET_PATTERNS:
            if re.search(pattern, line) and "example" not in line.lower() and "your_" not in line.lower():
                findings.append({
                    "file": filepath, "line": i, "severity": "严重",
                    "type": desc, "detail": line.strip()[:80]
                })
                break
        # 危险模式
        for pattern, desc, sev in DANGEROUS_PATTERNS:
            if re.search(pattern, line) and not re.search(r"^\s*(#|//|/\*)", line):
                findings.append({
                    "file": filepath, "line": i, "severity": sev,
                    "type": desc, "detail": line.strip()[:80]
                })
                break
    return findings


def scan_dir(dirpath):
    """扫描目录"""
    all_findings = []
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if Path(f).suffix in CODE_EXTS:
                all_findings.extend(scan_file(os.path.join(root, f)))
    return all_findings


def main():
    parser = argparse.ArgumentParser(description="DevFlow 深度安全审计")
    parser.add_argument("--dir", default=".", help="项目目录")
    parser.add_argument("--file", help="单个文件")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    if args.file:
        findings = scan_file(os.path.abspath(args.file))
    else:
        findings = scan_dir(os.path.abspath(args.dir))

    dep_issues = [] if args.file else check_dependencies(os.path.abspath(args.dir))

    if args.json:
        report = {
            "findings": findings,
            "dependency_issues": dep_issues,
            "total": len(findings) + len(dep_issues)
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("🔒 DevFlow 深度安全审计\n")

    if not findings and not dep_issues:
        print("✓ 未发现安全问题")
        return

    sev_order = {"严重": 0, "高": 1, "中": 2, "低": 3}
    for f in sorted(findings, key=lambda x: sev_order.get(x["severity"], 9)):
        icon = {"严重": "🔴", "高": "🟠", "中": "🟡", "低": "🔵"}.get(f["severity"], "⚪")
        print(f"  {icon} [{f['severity']}] {f['type']}")
        print(f"     {f['file']}:{f['line']}")
        print(f"     {f['detail']}")

    for d in dep_issues:
        print(f"  🟡 [依赖] {d}")

    print(f"\n共 {len(findings)} 处代码问题, {len(dep_issues)} 处依赖问题")
    if any(f["severity"] in ("严重", "高") for f in findings):
        sys.exit(1)


if __name__ == "__main__":
    main()

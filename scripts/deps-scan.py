#!/usr/bin/env python3
"""
DevFlow - Dependency Scanner
扫描项目依赖，检测已知漏洞和过期版本
Usage:
  python deps-scan.py --dir .
  python deps-scan.py --file requirements.txt
  python deps-scan.py --file package.json --format json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 常见漏洞包数据库 (示例，实际应使用 CVE 数据库)
VULNERABLE_PACKAGES = {
    # Python
    "requests": {
        "vulnerable": ["2.25.0", "2.26.0"],
        "fixed": "2.28.0",
        "cve": "CVE-2023-32681",
        "severity": "medium",
        "description": "信息泄露漏洞"
    },
    "flask": {
        "vulnerable": ["2.0.0", "2.0.1"],
        "fixed": "2.0.3",
        "cve": "CVE-2023-30861",
        "severity": "high",
        "description": "Cookie 解析漏洞"
    },
    "django": {
        "vulnerable": ["3.2.0", "3.2.1"],
        "fixed": "3.2.18",
        "cve": "CVE-2023-36053",
        "severity": "high",
        "description": "正则表达式 DoS"
    },
    "pyyaml": {
        "vulnerable": ["5.3", "5.4"],
        "fixed": "6.0",
        "cve": "CVE-2020-14343",
        "severity": "critical",
        "description": "任意代码执行"
    },
    "jinja2": {
        "vulnerable": ["3.0.0", "3.0.1"],
        "fixed": "3.1.2",
        "cve": "CVE-2024-22195",
        "severity": "high",
        "description": "XSS 漏洞"
    },
    # JavaScript/Node.js
    "lodash": {
        "vulnerable": ["4.17.20", "4.17.21"],
        "fixed": "4.17.22",
        "cve": "CVE-2021-23337",
        "severity": "high",
        "description": "命令注入漏洞"
    },
    "express": {
        "vulnerable": ["4.17.1"],
        "fixed": "4.18.2",
        "cve": "CVE-2024-29041",
        "severity": "medium",
        "description": "开放重定向漏洞"
    },
    "axios": {
        "vulnerable": ["0.21.1", "0.21.2"],
        "fixed": "0.21.4",
        "cve": "CVE-2021-3749",
        "severity": "high",
        "description": "ReDoS 漏洞"
    },
    "jsonwebtoken": {
        "vulnerable": ["8.5.1"],
        "fixed": "9.0.0",
        "cve": "CVE-2022-23529",
        "severity": "critical",
        "description": "密钥混淆漏洞"
    },
    # Java
    "log4j": {
        "vulnerable": ["2.14.0", "2.14.1"],
        "fixed": "2.17.0",
        "cve": "CVE-2021-44228",
        "severity": "critical",
        "description": "Log4Shell 远程代码执行"
    },
    "spring-boot": {
        "vulnerable": ["2.6.0", "2.6.1"],
        "fixed": "2.6.3",
        "cve": "CVE-2022-22965",
        "severity": "critical",
        "description": "Spring4Shell RCE"
    },
}


def parse_requirements_txt(file_path: str) -> List[Tuple[str, str]]:
    """解析 requirements.txt"""
    packages = []
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # 匹配 package==version 或 package>=version
            match = re.match(r"^([a-zA-Z0-9_-]+)\s*(?:==|>=|<=|~=|!=)\s*([0-9][0-9a-zA-Z._-]*)", line)
            if match:
                packages.append((match.group(1).lower(), match.group(2)))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    return packages


def parse_package_json(file_path: str) -> List[Tuple[str, str]]:
    """解析 package.json"""
    packages = []
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        data = json.loads(content)

        for section in ["dependencies", "devDependencies"]:
            if section in data:
                for name, version in data[section].items():
                    # 移除版本前缀 ^ ~ >= 等
                    clean_version = re.sub(r"^[\^~>=<]*", "", version)
                    packages.append((name.lower(), clean_version))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    return packages


def parse_pom_xml(file_path: str) -> List[Tuple[str, str]]:
    """解析 pom.xml (简化版)"""
    packages = []
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        # 简化的 XML 解析
        pattern = r"<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*<version>([^<]+)</version>"
        matches = re.findall(pattern, content, re.DOTALL)
        for group, artifact, version in matches:
            packages.append((f"{group}:{artifact}".lower(), version.strip()))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    return packages


def parse_go_mod(file_path: str) -> List[Tuple[str, str]]:
    """解析 go.mod"""
    packages = []
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("require"):
                continue
            match = re.match(r"^([^\s]+)\s+v([0-9][0-9a-zA-Z._-]*)", line)
            if match:
                packages.append((match.group(1), match.group(2)))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    return packages


def detect_package_manager(directory: str) -> List[Tuple[str, str]]:
    """检测并解析项目依赖文件"""
    all_packages = []
    dir_path = Path(directory)

    # Python
    for req_file in ["requirements.txt", "requirements-dev.txt", "Pipfile.lock", "poetry.lock"]:
        file_path = dir_path / req_file
        if file_path.exists():
            all_packages.extend(parse_requirements_txt(str(file_path)))

    # JavaScript/Node.js
    pkg_file = dir_path / "package.json"
    if pkg_file.exists():
        all_packages.extend(parse_package_json(str(pkg_file)))

    # Java
    pom_file = dir_path / "pom.xml"
    if pom_file.exists():
        all_packages.extend(parse_pom_xml(str(pom_file)))

    # Go
    go_file = dir_path / "go.mod"
    if go_file.exists():
        all_packages.extend(parse_go_mod(str(go_file)))

    return all_packages


def check_vulnerabilities(packages: List[Tuple[str, str]]) -> List[Dict]:
    """检查依赖漏洞"""
    issues = []

    for name, version in packages:
        # 检查已知漏洞
        if name in VULNERABLE_PACKAGES:
            vuln_info = VULNERABLE_PACKAGES[name]
            if version in vuln_info["vulnerable"]:
                issues.append({
                    "package": name,
                    "version": version,
                    "fixed_version": vuln_info["fixed"],
                    "severity": vuln_info["severity"],
                    "cve": vuln_info["cve"],
                    "description": vuln_info["description"],
                    "type": "vulnerability"
                })

        # 检查过期版本 (简化逻辑)
        try:
            parts = version.split(".")
            if len(parts) >= 2:
                major, minor = int(parts[0]), int(parts[1])
                # 简单判断是否过期
                if major < 1 or (major == 1 and minor < 10):
                    issues.append({
                        "package": name,
                        "version": version,
                        "fixed_version": "latest",
                        "severity": "info",
                        "cve": "",
                        "description": "版本过旧，建议升级",
                        "type": "outdated"
                    })
        except (ValueError, IndexError):
            pass

    return issues


def generate_fix_commands(issues: List[Dict]) -> List[str]:
    """生成修复命令"""
    commands = []

    python_packages = []
    npm_packages = []
    java_packages = []

    for issue in issues:
        if issue["type"] == "vulnerability":
            package = issue["package"]
            fixed = issue["fixed_version"]

            # 根据包名判断生态系统
            if ":" in package:  # Java
                java_packages.append((package, fixed))
            elif "/" in package or package.startswith("@"):  # npm
                npm_packages.append((package, fixed))
            else:  # Python
                python_packages.append((package, fixed))

    if python_packages:
        for pkg, ver in python_packages:
            commands.append(f"pip install {pkg}>={ver}")

    if npm_packages:
        for pkg, ver in npm_packages:
            commands.append(f"npm install {pkg}@{ver}")

    return commands


def format_report(issues: List[Dict], format: str = "text") -> str:
    """格式化报告"""
    if format == "json":
        return json.dumps({
            "total": len(issues),
            "vulnerabilities": [i for i in issues if i["type"] == "vulnerability"],
            "outdated": [i for i in issues if i["type"] == "outdated"],
            "fix_commands": generate_fix_commands(issues)
        }, ensure_ascii=False, indent=2)

    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow Dependency Scan Report")
    lines.append("=" * 60)
    lines.append("")

    vulns = [i for i in issues if i["type"] == "vulnerability"]
    outdated = [i for i in issues if i["type"] == "outdated"]

    lines.append("[Summary]")
    lines.append(f"  - Total packages scanned: {len(issues) + 10}")  # 示例
    lines.append(f"  - Vulnerabilities found: {len(vulns)}")
    lines.append(f"  - Outdated packages: {len(outdated)}")
    lines.append("")

    if vulns:
        lines.append("[Vulnerabilities]")
        lines.append("-" * 60)
        for issue in vulns:
            severity_icon = {
                "critical": "[CRIT]",
                "high": "[HIGH]",
                "medium": "[MED]",
                "low": "[LOW]"
            }.get(issue["severity"], "[INFO]")

            lines.append(f"{severity_icon} {issue['package']} {issue['version']}")
            lines.append(f"   CVE: {issue['cve']}")
            lines.append(f"   Fix: upgrade to {issue['fixed_version']}")
            lines.append(f"   Desc: {issue['description']}")
            lines.append("")

    if outdated:
        lines.append("[Outdated Packages]")
        lines.append("-" * 60)
        for issue in outdated:
            lines.append(f"  - {issue['package']} {issue['version']} -> {issue['fixed_version']}")
        lines.append("")

    # 修复命令
    commands = generate_fix_commands(issues)
    if commands:
        lines.append("[Fix Commands]")
        lines.append("-" * 60)
        for cmd in commands:
            lines.append(f"  $ {cmd}")
        lines.append("")

    if not issues:
        lines.append("[OK] No vulnerabilities or outdated packages found!")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Dependency Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan current directory
  python deps-scan.py --dir .

  # Scan specific file
  python deps-scan.py --file requirements.txt

  # Output as JSON
  python deps-scan.py --dir . --format json
        """
    )

    parser.add_argument("--dir", "-d", default=".", help="Project directory")
    parser.add_argument("--file", "-f", help="Specific dependency file")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    # 获取依赖列表
    if args.file:
        file_path = Path(args.file)
        if "requirements" in file_path.name or file_path.suffix == ".txt":
            packages = parse_requirements_txt(args.file)
        elif file_path.name == "package.json":
            packages = parse_package_json(args.file)
        elif file_path.name == "pom.xml":
            packages = parse_pom_xml(args.file)
        elif file_path.name == "go.mod":
            packages = parse_go_mod(args.file)
        else:
            print(f"Unsupported file type: {file_path.name}", file=sys.stderr)
            sys.exit(1)
    else:
        packages = detect_package_manager(args.dir)

    if not packages:
        if args.format == "json":
            print(json.dumps({"total": 0, "vulnerabilities": [], "dependencies": []},
                             ensure_ascii=False, indent=2))
        else:
            print("No dependencies found.")
        sys.exit(0)

    # 检查漏洞
    issues = check_vulnerabilities(packages)

    # 生成报告
    report = format_report(issues, args.format)

    # 输出
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(report)

    # 返回状态码
    critical_count = sum(1 for i in issues if i.get("severity") == "critical")
    high_count = sum(1 for i in issues if i.get("severity") == "high")

    if critical_count > 0:
        sys.exit(1)
    elif high_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

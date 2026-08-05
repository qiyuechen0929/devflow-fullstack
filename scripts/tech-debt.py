#!/usr/bin/env python3
"""
DevFlow - Technical Debt Tracker
追踪待优化项
Usage:
  python tech-debt.py --dir src/
  python tech-debt.py --file main.py
  python tech-debt.py --add "Refactor auth module" --priority high
  python tech-debt.py --list
  python tech-debt.py --report
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 技术债务存储
DEBT_FILE = Path.home() / ".devflow" / "tech-debt.json"

# 债务类型
DEBT_TYPES = {
    "code_smell": {"title": "Code Smell", "severity": "medium"},
    "duplication": {"title": "Code Duplication", "severity": "high"},
    "complexity": {"title": "High Complexity", "severity": "high"},
    "todo": {"title": "TODO/FIXME", "severity": "low"},
    "deprecated": {"title": "Deprecated Code", "severity": "medium"},
    "missing_tests": {"title": "Missing Tests", "severity": "high"},
    "missing_docs": {"title": "Missing Documentation", "severity": "low"},
    "performance": {"title": "Performance Issue", "severity": "medium"},
    "security": {"title": "Security Issue", "severity": "critical"},
    "dependency": {"title": "Outdated Dependency", "severity": "medium"},
}


def ensure_debt_file():
    """确保债务文件存在"""
    DEBT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DEBT_FILE.exists():
        DEBT_FILE.write_text(json.dumps({"debts": [], "created_at": datetime.now().isoformat()}, indent=2), encoding="utf-8")


def load_debts() -> List[Dict]:
    """加载债务列表"""
    ensure_debt_file()
    try:
        data = json.loads(DEBT_FILE.read_text(encoding="utf-8"))
        return data.get("debts", [])
    except Exception:
        return []


def save_debts(debts: List[Dict]):
    """保存债务列表"""
    ensure_debt_file()
    data = {
        "debts": debts,
        "updated_at": datetime.now().isoformat()
    }
    DEBT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add_debt(description: str, priority: str = "medium", debt_type: str = "code_smell",
             file_path: str = None, line: int = None) -> Dict:
    """添加技术债务"""
    debts = load_debts()

    debt = {
        "id": len(debts) + 1,
        "description": description,
        "priority": priority,
        "type": debt_type,
        "file": file_path,
        "line": line,
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "resolved_at": None,
        "notes": []
    }

    debts.append(debt)
    save_debts(debts)

    return debt


def resolve_debt(debt_id: int) -> bool:
    """解决技术债务"""
    debts = load_debts()

    for debt in debts:
        if debt["id"] == debt_id:
            debt["status"] = "resolved"
            debt["resolved_at"] = datetime.now().isoformat()
            save_debts(debts)
            return True

    return False


def add_note(debt_id: int, note: str) -> bool:
    """添加备注"""
    debts = load_debts()

    for debt in debts:
        if debt["id"] == debt_id:
            debt["notes"].append({
                "text": note,
                "created_at": datetime.now().isoformat()
            })
            save_debts(debts)
            return True

    return False


def delete_debt(debt_id: int) -> bool:
    """删除技术债务"""
    debts = load_debts()
    debts = [d for d in debts if d["id"] != debt_id]
    save_debts(debts)
    return True


def scan_code_debts(directory: str) -> List[Dict]:
    """扫描代码中的技术债务"""
    found_debts = []
    dir_path = Path(directory)

    # 扫描 TODO/FIXME
    patterns = [
        (r"TODO[:\s]+(.*)", "todo", "low"),
        (r"FIXME[:\s]+(.*)", "todo", "medium"),
        (r"HACK[:\s]+(.*)", "code_smell", "high"),
        (r"XXX[:\s]+(.*)", "code_smell", "medium"),
        (r"DEPRECATED[:\s]+(.*)", "deprecated", "medium"),
    ]

    for file_path in dir_path.rglob("*"):
        if any(part.startswith(".") or part in ("node_modules", "vendor", "dist", "build", "__pycache__")
               for part in file_path.parts):
            continue

        if file_path.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go") and file_path.is_file():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")

                for i, line in enumerate(lines, 1):
                    for pattern, debt_type, severity in patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            description = match.group(1).strip() if match.group(1) else line.strip()
                            found_debts.append({
                                "file": str(file_path),
                                "line": i,
                                "type": debt_type,
                                "priority": severity,
                                "description": description
                            })
            except Exception:
                continue

    return found_debts


def list_debts(status: str = None, priority: str = None) -> List[Dict]:
    """列出技术债务"""
    debts = load_debts()

    if status:
        debts = [d for d in debts if d["status"] == status]

    if priority:
        debts = [d for d in debts if d["priority"] == priority]

    return debts


def generate_report(debts: List[Dict]) -> Dict:
    """生成报告"""
    total = len(debts)
    open_debts = [d for d in debts if d["status"] == "open"]
    resolved_debts = [d for d in debts if d["status"] == "resolved"]

    # 按优先级统计
    by_priority = {}
    for debt in open_debts:
        priority = debt["priority"]
        by_priority[priority] = by_priority.get(priority, 0) + 1

    # 按类型统计
    by_type = {}
    for debt in open_debts:
        debt_type = debt["type"]
        by_type[debt_type] = by_type.get(debt_type, 0) + 1

    # 计算债务指数
    priority_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    debt_index = sum(priority_weights.get(d["priority"], 1) for d in open_debts)

    return {
        "total": total,
        "open": len(open_debts),
        "resolved": len(resolved_debts),
        "by_priority": by_priority,
        "by_type": by_type,
        "debt_index": debt_index,
        "resolution_rate": len(resolved_debts) / total * 100 if total > 0 else 0
    }


def format_report(debts: List[Dict], report: Dict, format: str = "text") -> str:
    """格式化报告"""
    if format == "json":
        return json.dumps({
            "report": report,
            "debts": debts
        }, indent=2, ensure_ascii=False)

    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow Technical Debt Report")
    lines.append("=" * 60)
    lines.append("")
    lines.append("[Summary]")
    lines.append(f"  Total debts: {report['total']}")
    lines.append(f"  Open: {report['open']}")
    lines.append(f"  Resolved: {report['resolved']}")
    lines.append(f"  Resolution rate: {report['resolution_rate']:.1f}%")
    lines.append(f"  Debt index: {report['debt_index']}")
    lines.append("")

    # 按优先级统计
    if report["by_priority"]:
        lines.append("[By Priority]")
        for priority in ["critical", "high", "medium", "low"]:
            count = report["by_priority"].get(priority, 0)
            if count > 0:
                lines.append(f"  {priority}: {count}")
        lines.append("")

    # 按类型统计
    if report["by_type"]:
        lines.append("[By Type]")
        for debt_type, count in sorted(report["by_type"].items(), key=lambda x: -x[1]):
            type_name = DEBT_TYPES.get(debt_type, {}).get("title", debt_type)
            lines.append(f"  {type_name}: {count}")
        lines.append("")

    # 列出开放的债务
    open_debts = [d for d in debts if d["status"] == "open"]
    if open_debts:
        lines.append("[Open Debts]")
        lines.append("-" * 60)
        for debt in open_debts[:20]:
            lines.append(f"  #{debt['id']} [{debt['priority']}] {debt['description']}")
            if debt.get("file"):
                lines.append(f"    File: {debt['file']}:{debt.get('line', '?')}")
        lines.append("")

    if not debts:
        lines.append("[OK] No technical debts tracked!")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Technical Debt Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan code for debts
  python tech-debt.py --dir src/ --scan

  # Add a debt
  python tech-debt.py --add "Refactor auth module" --priority high

  # List open debts
  python tech-debt.py --list

  # Resolve a debt
  python tech-debt.py --resolve 1

  # Generate report
  python tech-debt.py --report

  # Output as JSON
  python tech-debt.py --report --format json
        """
    )

    parser.add_argument("--scan", action="store_true", help="Scan code for debts")
    parser.add_argument("--add", help="Add a new debt")
    parser.add_argument("--resolve", type=int, help="Resolve a debt by ID")
    parser.add_argument("--delete", type=int, help="Delete a debt by ID")
    parser.add_argument("--note", help="Add note to debt (use with --id)")
    parser.add_argument("--id", type=int, help="Debt ID for note")
    parser.add_argument("--list", action="store_true", help="List debts")
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--dir", "-d", help="Directory to scan")
    parser.add_argument("--priority", choices=["critical", "high", "medium", "low"], default="medium",
                        help="Debt priority")
    parser.add_argument("--type", choices=list(DEBT_TYPES.keys()), default="code_smell", help="Debt type")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    # 扫描代码
    if args.scan:
        if not args.dir:
            print("Error: --dir is required for --scan", file=sys.stderr)
            sys.exit(1)

        found_debts = scan_code_debts(args.dir)
        print(f"Found {len(found_debts)} potential debts in code")

        for debt in found_debts[:10]:
            print(f"  [{debt['priority']}] {debt['file']}:{debt['line']} - {debt['description'][:50]}")

        return

    # 添加债务
    if args.add:
        debt = add_debt(args.add, args.priority, args.type)
        print(f"Added debt #{debt['id']}: {args.add}")
        return

    # 解决债务
    if args.resolve:
        if resolve_debt(args.resolve):
            print(f"Resolved debt #{args.resolve}")
        else:
            print(f"Debt #{args.resolve} not found")
        return

    # 删除债务
    if args.delete:
        delete_debt(args.delete)
        print(f"Deleted debt #{args.delete}")
        return

    # 添加备注
    if args.note and args.id:
        if add_note(args.id, args.note):
            print(f"Added note to debt #{args.id}")
        else:
            print(f"Debt #{args.id} not found")
        return

    # 列出债务
    if args.list:
        debts = list_debts()
        if debts:
            print("Technical Debts:")
            for debt in debts:
                status = "[x]" if debt["status"] == "resolved" else "[ ]"
                print(f"  {status} #{debt['id']} [{debt['priority']}] {debt['description']}")
        else:
            print("No technical debts tracked.")
        return

    # 生成报告
    if args.report:
        debts = list_debts()
        report = generate_report(debts)
        output = format_report(debts, report, args.format)

        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Report saved to: {args.output}")
        else:
            print(output)
        return

    # 默认显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()

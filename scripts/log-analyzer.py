#!/usr/bin/env python3
"""
DevFlow - Log Analyzer
解析应用日志
Usage:
  python log-analyzer.py --file app.log
  python log-analyzer.py --file app.log --mode errors
  python log-analyzer.py --dir logs/
  python log-analyzer.py --file app.log --pattern "ERROR|WARN"
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 常见日志格式
LOG_PATTERNS = {
    # Apache/Nginx 格式
    "apache": r'(?P<ip>[\d.]+) - - \[(?P<time>[^\]]+)\] "(?P<method>\w+) (?P<path>[^"]+) HTTP/[\d.]+" (?P<status>\d+) (?P<size>\d+)',
    # JSON 格式
    "json": r'^\{.*\}$',
    # 通用格式
    "common": r'(?P<time>\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}[.\d]*)\s+(?P<level>\w+)\s+(?P<message>.*)',
    # Python logging 格式
    "python": r'(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) - (?P<name>\w+) - (?P<level>\w+) - (?P<message>.*)',
    # Node.js 格式
    "node": r'\[(?P<time>[^\]]+)\]\s+(?P<level>\w+):\s+(?P<message>.*)',
}


def detect_log_format(content: str) -> str:
    """检测日志格式"""
    lines = content.split("\n")[:100]

    for format_name, pattern in LOG_PATTERNS.items():
        matches = sum(1 for line in lines if re.match(pattern, line.strip()))
        if matches > len(lines) * 0.5:
            return format_name

    return "common"


def parse_log_line(line: str, format: str = "common") -> Optional[Dict]:
    """解析单行日志"""
    line = line.strip()
    if not line:
        return None

    # JSON 格式
    if format == "json":
        try:
            data = json.loads(line)
            return {
                "time": data.get("timestamp", data.get("time", "")),
                "level": data.get("level", data.get("severity", "INFO")).upper(),
                "message": data.get("message", data.get("msg", "")),
                "extra": {k: v for k, v in data.items() if k not in ("timestamp", "time", "level", "severity", "message", "msg")}
            }
        except json.JSONDecodeError:
            pass

    # 正则匹配
    pattern = LOG_PATTERNS.get(format, LOG_PATTERNS["common"])
    match = re.match(pattern, line)

    if match:
        data = match.groupdict()
        return {
            "time": data.get("time", ""),
            "level": data.get("level", "INFO").upper(),
            "message": data.get("message", line),
            "extra": {k: v for k, v in data.items() if k not in ("time", "level", "message")}
        }

    # 默认返回
    return {
        "time": "",
        "level": "UNKNOWN",
        "message": line,
        "extra": {}
    }


def parse_log_file(file_path: str, format: str = "auto") -> List[Dict]:
    """解析日志文件"""
    entries = []

    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")

        # 自动检测格式
        if format == "auto":
            format = detect_log_format(content)

        for line in content.split("\n"):
            entry = parse_log_line(line, format)
            if entry:
                entry["file"] = file_path
                entries.append(entry)

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return entries


def scan_directory(directory: str, format: str = "auto") -> List[Dict]:
    """扫描目录中的日志文件"""
    all_entries = []
    dir_path = Path(directory)

    for file_path in dir_path.rglob("*"):
        if any(part.startswith(".") or part in ("node_modules", "vendor", "dist", "build")
               for part in file_path.parts):
            continue

        if file_path.suffix in (".log", ".txt", ".out", ".err") and file_path.is_file():
            entries = parse_log_file(str(file_path), format)
            all_entries.extend(entries)

    return all_entries


def analyze_entries(entries: List[Dict]) -> Dict:
    """分析日志条目"""
    if not entries:
        return {}

    # 按级别统计
    level_counts = Counter(entry["level"] for entry in entries)

    # 按时间统计
    time_counts = Counter()
    for entry in entries:
        if entry.get("time"):
            # 提取日期
            date_match = re.match(r"(\d{4}-\d{2}-\d{2})", entry["time"])
            if date_match:
                time_counts[date_match.group(1)] += 1

    # 错误消息
    errors = [entry for entry in entries if entry["level"] in ("ERROR", "CRIT", "FATAL")]
    error_messages = Counter(entry["message"][:100] for entry in errors)

    # 警告消息
    warnings = [entry for entry in entries if entry["level"] in ("WARN", "WARNING")]
    warning_messages = Counter(entry["message"][:100] for entry in warnings)

    # 按小时分布
    hour_counts = Counter()
    for entry in entries:
        if entry.get("time"):
            hour_match = re.search(r"(\d{2}):\d{2}:\d{2}", entry["time"])
            if hour_match:
                hour_counts[hour_match.group(1)] += 1

    return {
        "total": len(entries),
        "levels": dict(level_counts),
        "dates": dict(time_counts),
        "hours": dict(hour_counts),
        "top_errors": error_messages.most_common(10),
        "top_warnings": warning_messages.most_common(10),
        "error_count": len(errors),
        "warning_count": len(warnings)
    }


def filter_entries(entries: List[Dict], level: str = None, pattern: str = None,
                   start_time: str = None, end_time: str = None) -> List[Dict]:
    """过滤日志条目"""
    filtered = entries

    # 按级别过滤
    if level:
        level_upper = level.upper()
        filtered = [e for e in filtered if e["level"] == level_upper]

    # 按模式过滤
    if pattern:
        regex = re.compile(pattern, re.IGNORECASE)
        filtered = [e for e in filtered if regex.search(e["message"])]

    # 按时间过滤
    if start_time:
        filtered = [e for e in filtered if e.get("time", "") >= start_time]

    if end_time:
        filtered = [e for e in filtered if e.get("time", "") <= end_time]

    return filtered


def format_report(entries: List[Dict], analysis: Dict, format: str = "text") -> str:
    """格式化报告"""
    if format == "json":
        return json.dumps({
            "analysis": analysis,
            "entries": entries[:1000]  # 限制输出数量
        }, indent=2, ensure_ascii=False)

    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow Log Analyzer Report")
    lines.append("=" * 60)
    lines.append("")

    lines.append("[Summary]")
    lines.append(f"  Total entries: {analysis.get('total', 0)}")
    lines.append(f"  Errors: {analysis.get('error_count', 0)}")
    lines.append(f"  Warnings: {analysis.get('warning_count', 0)}")
    lines.append("")

    # 级别分布
    if analysis.get("levels"):
        lines.append("[Log Levels]")
        for level, count in sorted(analysis["levels"].items(), key=lambda x: -x[1]):
            lines.append(f"  {level}: {count}")
        lines.append("")

    # 日期分布
    if analysis.get("dates"):
        lines.append("[Date Distribution]")
        for date, count in sorted(analysis["dates"].items())[-10:]:
            lines.append(f"  {date}: {count}")
        lines.append("")

    # 小时分布
    if analysis.get("hours"):
        lines.append("[Hour Distribution]")
        for hour in sorted(analysis["hours"].keys()):
            count = analysis["hours"][hour]
            lines.append(f"  {hour}:00: {count}")
        lines.append("")

    # Top 错误
    if analysis.get("top_errors"):
        lines.append("[Top Errors]")
        for msg, count in analysis["top_errors"]:
            lines.append(f"  ({count}x) {msg}")
        lines.append("")

    # Top 警告
    if analysis.get("top_warnings"):
        lines.append("[Top Warnings]")
        for msg, count in analysis["top_warnings"]:
            lines.append(f"  ({count}x) {msg}")
        lines.append("")

    # 最近日志
    lines.append("[Recent Entries]")
    lines.append("-" * 60)
    for entry in entries[-20:]:
        time_str = f"[{entry['time']}] " if entry.get("time") else ""
        lines.append(f"{time_str}{entry['level']}: {entry['message'][:100]}")
    lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Log Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze log file
  python log-analyzer.py --file app.log

  # Show only errors
  python log-analyzer.py --file app.log --level ERROR

  # Search for pattern
  python log-analyzer.py --file app.log --pattern "timeout|connection"

  # Analyze directory
  python log-analyzer.py --dir logs/

  # Output as JSON
  python log-analyzer.py --file app.log --format json

  # Save report
  python log-analyzer.py --file app.log --output report.txt
        """
    )

    parser.add_argument("--file", "-f", help="Log file to analyze")
    parser.add_argument("--dir", "-d", help="Directory to scan")
    parser.add_argument("--format", choices=["auto", "apache", "json", "common", "python", "node"],
                        default="auto", help="Log format")
    parser.add_argument("--level", "-l", help="Filter by log level")
    parser.add_argument("--pattern", "-p", help="Filter by regex pattern")
    parser.add_argument("--start-time", help="Start time filter")
    parser.add_argument("--end-time", help="End time filter")
    parser.add_argument("--output-format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    if not args.file and not args.dir:
        print("Error: --file or --dir is required", file=sys.stderr)
        sys.exit(1)

    # 解析日志
    if args.file:
        entries = parse_log_file(args.file, args.format)
    else:
        entries = scan_directory(args.dir, args.format)

    if not entries:
        print("No log entries found.", file=sys.stderr)
        sys.exit(0)

    # 过滤
    entries = filter_entries(entries, args.level, args.pattern, args.start_time, args.end_time)

    # 分析
    analysis = analyze_entries(entries)

    # 生成报告
    report = format_report(entries, analysis, args.output_format)

    # 输出
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()

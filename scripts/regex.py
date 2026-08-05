#!/usr/bin/env python3
"""
DevFlow - Regex Generator & Debugger (#5, #14)
Usage:
  python regex.py --gen "match Chinese phone numbers"
  python regex.py --test "13812345678" --pattern "^1[3-9]\\d{9}$"
  python regex.py --explain "^(\d{3})-(\d{4})$"
"""

import argparse, re, textwrap

PATTERNS = {
    "chinese phone": (r"^1[3-9]\d{9}$", "中国大陆手机号"),
    "email": (r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", "邮箱地址"),
    "url": (r"^https?://[^\s/$.?#].[^\s]*$", "HTTP/HTTPS URL"),
    "ipv4": (r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$", "IPv4地址"),
    "date ymd": (r"^\d{4}-\d{2}-\d{2}$", "日期 YYYY-MM-DD"),
    "id card": (r"^\d{17}[\dXx]$", "中国身份证号"),
    "hex color": (r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$", "十六进制颜色"),
    "chinese": (r"[\u4e00-\u9fff]+", "中文字符"),
    "whitespace": (r"\s+", "空白字符"),
    "number": (r"^-?\d+(\.\d+)?$", "数字(含小数)"),
    "word": (r"\b\w+\b", "单词"),
}

def explain_pattern(pattern):
    """Explain what a regex does"""
    parts = []
    if pattern.startswith("^"): parts.append("从开头匹配")
    if pattern.endswith("$"): parts.append("到结尾匹配")
    if "\\d" in pattern: parts.append("数字 \\d")
    if "\\w" in pattern: parts.append("字母数字下划线 \\w")
    if "\\s" in pattern: parts.append("空白字符 \\s")
    if "+" in pattern: parts.append("一个或多个 +")
    if "*" in pattern: parts.append("零个或多个 *")
    if "?" in pattern and "?:" not in pattern: parts.append("可选 ?")
    if "[" in pattern: parts.append("字符集 [...]")
    if "|" in pattern: parts.append("或 |")
    if "(" in pattern and "?:" not in pattern: parts.append("捕获组 ()")
    if "[^" in pattern: parts.append("排除字符集 [^...]")
    if "." in pattern and "\\." not in pattern: parts.append("任意字符 .")
    if "{n}" in pattern: parts.append("精确次数 {n}")
    if "{n,m}" in pattern: parts.append("范围次数 {n,m}")
    return parts if parts else ["未识别出典型元素"]

def test_pattern(text, pattern):
    """Test a regex against input"""
    try:
        r = re.compile(pattern)
        m = r.search(text)
        if m:
            result = [f"匹配成功: '{m.group()}'"]
            if m.groups():
                for i, g in enumerate(m.groups(), 1):
                    result.append(f"  分组{i}: '{g}'")
            result.append(f"  位置: {m.start()}-{m.end()}")
            # Show all matches
            all_m = r.findall(text)
            if len(all_m) > 1:
                result.append(f"  共匹配 {len(all_m)} 处")
            return "\n".join(result)
        else:
            return f"未匹配"
    except re.error as e:
        return f"正则错误: {e}"

def generate_pattern(description):
    """Simple keyword-based pattern generation"""
    desc = description.lower()
    for keyword, (pattern, name) in PATTERNS.items():
        if keyword in desc:
            return f"{name}: `{pattern}`\n用法: {explain_pattern_as_text(pattern)}"
    return "未找到匹配的预设模式。请描述更具体的需求。"

def explain_pattern_as_text(pattern):
    parts = explain_pattern(pattern)
    return ", ".join(parts)

def main():
    parser = argparse.ArgumentParser(description="Regex Generator & Debugger")
    parser.add_argument("--gen", help="自然语言描述，生成正则")
    parser.add_argument("--test", help="测试文本")
    parser.add_argument("--pattern", help="正则表达式")
    parser.add_argument("--explain", help="解释正则")
    args = parser.parse_args()

    if args.explain:
        parts = explain_pattern(args.explain)
        print(f"正则: `{args.explain}`")
        for p in parts:
            print(f"  - {p}")

    elif args.gen:
        print(generate_pattern(args.gen))

    elif args.test and args.pattern:
        print(test_pattern(args.test, args.pattern))

    else:
        parser.print_help()

if __name__ == "__main__":
    main()

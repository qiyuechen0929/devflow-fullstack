#!/usr/bin/env python3
"""
DevFlow - API Integration Helper (#8) + Log Analyzer (#10) + Deps Health (#16)
Usage:
  python apitools.py --mode curl --input "curl -X POST https://api.example.com/users"
  python apitools.py --mode log --file error.log
  python apitools.py --mode deps --file package.json
"""

import argparse, os, re, json
from pathlib import Path

# ─── Curl → Code ───
def parse_curl(curl_cmd):
    method = "GET"
    url = ""
    headers = {}
    body = None
    lang = "python"

    tokens = re.findall(r"""(?:[^\s"']+|"[^"]*"|'[^']*')""", curl_cmd)
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "curl":
            pass
        elif t in ("-X", "--request"):
            i += 1
            method = tokens[i].strip("'\"")
        elif t in ("-H", "--header"):
            i += 1
            kv = tokens[i].strip("'\"")
            if ":" in kv:
                k, v = kv.split(":", 1)
                headers[k.strip()] = v.strip()
        elif t in ("-d", "--data", "--data-raw"):
            i += 1
            body = tokens[i].strip("'\"")
        elif t.startswith("http"):
            url = t.strip("'\"")
        i += 1

    # Generate code
    if lang == "python":
        code = [f"import requests", f"", f"url = \"{url}\"", f"headers = {json.dumps(headers, indent=4)}"]
        if body:
            code.append(f"data = {json.dumps(body) if not body.startswith('{') else body}")
            code.append(f"response = requests.{method.lower()}(url, headers=headers, json=data)")
        else:
            code.append(f"response = requests.{method.lower()}(url, headers=headers)")
        code.extend(["", "print(response.status_code)", "print(response.json())"])

    elif lang == "javascript":
        code = [f"const url = '{url}'", f"const options = {{", f"  method: '{method}',",
                f"  headers: {json.dumps(headers, indent=2)},"]
        if body:
            code.append(f"  body: JSON.stringify({body})")
        code.append(f"}};")
        code.append(f"fetch(url, options).then(r => r.json()).then(console.log)")

    return f"# {method} {url}\n" + "\n".join(code)

# ─── Log Analyzer ───
def analyze_log(content):
    patterns = {
        "NullPointer": ("空指针异常", "检查对象是否为空后再调用方法"),
        "IndexError|index out of range|ArrayIndexOutOfBounds": ("数组越界", "检查数组长度和索引范围"),
        "KeyError|KeyError": ("键不存在", "使用 dict.get() 或检查键是否存在"),
        "Connection refused|ECONNREFUSED": ("连接被拒绝", "检查目标服务是否启动、端口是否正确"),
        "Timeout|timed out": ("超时", "增加超时时间或优化被调用方"),
        "OutOfMemory|MemoryError": ("内存溢出", "检查内存泄漏、减少数据缓存"),
        "ModuleNotFound|ImportError|No module named": ("模块未找到", "pip install 缺失的依赖"),
        "SyntaxError": ("语法错误", "检查拼写、缩进、括号匹配"),
        "TypeError": ("类型错误", "检查变量类型、参数传递"),
        "Permission denied|EACCES": ("权限不足", "检查文件/目录权限"),
    }

    results = []
    for pattern, (cause, fix) in patterns.items():
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            results.append(f"## {cause}")
            results.append(f"- 匹配: `{m.group()}`")
            results.append(f"- 修复: {fix}")
            results.append("")

    if not results:
        results.append("未识别出常见错误模式。请粘贴完整堆栈信息。")

    # Find file:line references
    locations = re.findall(r"(File\s+[\"']?([^\"']+)[\"']?,\s*line\s+(\d+))|(at\s+(\S+)\((\S+):(\d+)\))", content)
    if locations:
        results.append("\n## 出错位置")
        seen = set()
        for loc in locations:
            if loc[0] and loc[0] not in seen:
                seen.add(loc[0])
                results.append(f"- {loc[0]}")
            elif loc[3] and loc[3] not in seen:
                seen.add(loc[3])
                results.append(f"- {loc[3]}")

    return "\n".join(results)

# ─── Dependency Health ───
def check_deps(filepath):
    p = Path(filepath)
    if not p.exists():
        return f"文件不存在: {filepath}"

    content = p.read_text(encoding="utf-8", errors="ignore")

    if p.name == "package.json":
        try:
            data = json.loads(content)
            deps = {**data.get("dependencies",{}), **data.get("devDependencies",{})}
            return analyze_npm_deps(deps)
        except json.JSONDecodeError:
            return "package.json 格式错误"

    elif p.name == "requirements.txt":
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        return f"依赖总数: {len(lines)}\n\n" + "\n".join(f"- {l}" for l in lines[:20]) + \
               (f"\n... 共{len(lines)}个" if len(lines) > 20 else "")

    elif p.name == "pom.xml":
        artifacts = re.findall(r"<artifactId>([^<]+)</artifactId>", content)
        versions = re.findall(r"<version>([^<]+)</version>", content)
        result = [f"依赖总数: {len(artifacts)}"]
        for a, v in zip(artifacts, versions):
            if "SNAPSHOT" in v:
                result.append(f"- [!!] {a}: SNAPSHOT 版本不稳定")
        return "\n".join(result)

    return "不支持的文件类型"

def analyze_npm_deps(deps):
    result = [f"依赖总数: {len(deps)}"]
    # Check for common issues
    for name, ver in sorted(deps.items()):
        v = ver.replace("^","").replace("~","")
        if name.startswith("@"): continue
        # Check for deprecated packages
        deprecated = {"request":"用 node-fetch/axios 替代","left-pad":"已废弃",
                      "core-js@2":"升级到 core-js@3","moment":"用 dayjs 替代"}
        for key, advice in deprecated.items():
            if key in name:
                result.append(f"- [!] {name}: {advice}")
                break
    return "\n".join(result)

def main():
    parser = argparse.ArgumentParser(description="API Tools (Curl/Log/Deps)")
    parser.add_argument("--mode", choices=["curl","log","deps"], required=True)
    parser.add_argument("--input", help="curl 命令或日志文件路径")
    parser.add_argument("--file", help="依赖文件路径")
    args = parser.parse_args()

    if args.mode == "curl" and args.input:
        print(parse_curl(args.input))
    elif args.mode == "log" and args.file:
        content = Path(args.file).read_text(encoding="utf-8", errors="ignore")
        print(analyze_log(content))
    elif args.mode == "deps" and args.file:
        print(check_deps(args.file))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

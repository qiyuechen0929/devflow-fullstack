#!/usr/bin/env python3
"""
DevFlow - API Documentation Generator
生成 Swagger/OpenAPI 文档
Usage:
  python api-docgen.py --file app.py
  python api-docgen.py --dir src/
  python api-docgen.py --file app.py --format openapi
  python api-docgen.py --file app.py --output api-docs.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional


def parse_flask_routes(content: str, file_path: str) -> List[Dict]:
    """解析 Flask 路由"""
    routes = []

    # 匹配 @app.route 或 @blueprint.route
    pattern = r'@(?:app|bp|blueprint)\.route\s*\(\s*["\']([^"\']+)["\']\s*(?:,\s*methods\s*=\s*\[([^\]]+)\])?\s*\)'
    matches = re.finditer(pattern, content)

    for match in matches:
        path = match.group(1)
        methods = match.group(2)
        if methods:
            methods = [m.strip().strip("'\"") for m in methods.split(",")]
        else:
            methods = ["GET"]

        # 查找函数定义
        func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', content[match.end():match.end()+500])
        func_name = func_match.group(1) if func_match else "unknown"
        params = func_match.group(2) if func_match else ""

        # 查找 docstring
        doc_match = re.search(r'"""([^"]+)"""', content[match.end():match.end()+1000])
        description = doc_match.group(1).strip() if doc_match else ""

        routes.append({
            "path": path,
            "methods": methods,
            "function": func_name,
            "params": params,
            "description": description,
            "file": file_path
        })

    return routes


def parse_fastapi_routes(content: str, file_path: str) -> List[Dict]:
    """解析 FastAPI 路由"""
    routes = []

    # 匹配 @app.get/post/put/delete 等
    pattern = r'@(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
    matches = re.finditer(pattern, content)

    for match in matches:
        method = match.group(1).upper()
        path = match.group(2)

        # 查找函数定义
        func_match = re.search(r'async\s+def\s+(\w+)\s*\(([^)]*)\)', content[match.end():match.end()+500])
        if not func_match:
            func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', content[match.end():match.end()+500])

        func_name = func_match.group(1) if func_match else "unknown"
        params = func_match.group(2) if func_match else ""

        # 查找 docstring
        doc_match = re.search(r'"""([^"]+)"""', content[match.end():match.end()+1000])
        description = doc_match.group(1).strip() if doc_match else ""

        routes.append({
            "path": path,
            "methods": [method],
            "function": func_name,
            "params": params,
            "description": description,
            "file": file_path
        })

    return routes


def parse_express_routes(content: str, file_path: str) -> List[Dict]:
    """解析 Express.js 路由"""
    routes = []

    # 匹配 app.get/post/put/delete 等
    pattern = r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
    matches = re.finditer(pattern, content)

    for match in matches:
        method = match.group(1).upper()
        path = match.group(2)

        # 查找回调函数
        func_match = re.search(r'(?:function\s+(\w+)|(?:req|request)\s*,\s*(?:res|response)\s*(?:,\s*next)?)', content[match.end():match.end()+500])
        func_name = func_match.group(1) if func_match else "anonymous"

        routes.append({
            "path": path,
            "methods": [method],
            "function": func_name,
            "params": "",
            "description": "",
            "file": file_path
        })

    return routes


def analyze_file(file_path: str) -> List[Dict]:
    """分析单个文件"""
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        ext = Path(file_path).suffix

        # 根据文件类型选择解析器
        if ext == ".py":
            if "flask" in content.lower() or "@app.route" in content:
                return parse_flask_routes(content, file_path)
            elif "fastapi" in content.lower() or "@app.get" in content:
                return parse_fastapi_routes(content, file_path)
        elif ext in (".js", ".ts"):
            if "express" in content.lower() or "app.get" in content:
                return parse_express_routes(content, file_path)

        return []
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
        return []


def scan_directory(directory: str) -> List[Dict]:
    """扫描目录"""
    all_routes = []
    dir_path = Path(directory)

    for file_path in dir_path.rglob("*"):
        # 跳过忽略的目录
        if any(part.startswith(".") or part in ("node_modules", "vendor", "dist", "build", "__pycache__")
               for part in file_path.parts):
            continue

        if file_path.suffix in (".py", ".js", ".ts") and file_path.is_file():
            routes = analyze_file(str(file_path))
            all_routes.extend(routes)

    return all_routes


def generate_openapi(routes: List[Dict], title: str = "API Documentation", version: str = "1.0.0") -> Dict:
    """生成 OpenAPI 规范"""
    openapi = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": "Generated by DevFlow"
        },
        "paths": {}
    }

    for route in routes:
        path = route["path"]

        # 转换路径格式
        path = re.sub(r"<(\w+)>", r"{\1}", path)

        if path not in openapi["paths"]:
            openapi["paths"][path] = {}

        for method in route["methods"]:
            method_lower = method.lower()

            operation = {
                "summary": route.get("description", ""),
                "operationId": route.get("function", ""),
                "responses": {
                    "200": {
                        "description": "Successful response"
                    }
                }
            }

            # 解析参数
            if route.get("params"):
                parameters = []
                for param in route["params"].split(","):
                    param = param.strip()
                    if param and param not in ("self", "request", "response", "req", "res", "next"):
                        # 移除类型注解
                        param_name = param.split(":")[0].strip().split("=")[0].strip()
                        if param_name and not param_name.startswith("*"):
                            parameters.append({
                                "name": param_name,
                                "in": "path" if "{" + param_name + "}" in path else "query",
                                "required": "{" + param_name + "}" in path,
                                "schema": {"type": "string"}
                            })

                if parameters:
                    operation["parameters"] = parameters

            openapi["paths"][path][method_lower] = operation

    return openapi


def generate_markdown(routes: List[Dict]) -> str:
    """生成 Markdown 文档"""
    lines = []
    lines.append("# API Documentation")
    lines.append("")
    lines.append(f"Generated by DevFlow")
    lines.append("")
    lines.append(f"Total endpoints: {len(routes)}")
    lines.append("")

    # 按路径分组
    by_path = {}
    for route in routes:
        path = route["path"]
        if path not in by_path:
            by_path[path] = []
        by_path[path].append(route)

    for path, path_routes in sorted(by_path.items()):
        lines.append(f"## {path}")
        lines.append("")

        for route in path_routes:
            methods = ", ".join(route["methods"])
            lines.append(f"### {methods}")
            lines.append("")
            lines.append(f"- **Function**: `{route.get('function', 'unknown')}`")

            if route.get("description"):
                lines.append(f"- **Description**: {route['description']}")

            if route.get("params"):
                lines.append(f"- **Parameters**: `{route['params']}`")

            lines.append("")

    return "\n".join(lines)


def format_report(routes: List[Dict], format: str = "text") -> str:
    """格式化报告"""
    if format == "json":
        return json.dumps({
            "total": len(routes),
            "routes": routes
        }, indent=2, ensure_ascii=False)

    if format == "openapi":
        openapi = generate_openapi(routes)
        return json.dumps(openapi, indent=2, ensure_ascii=False)

    if format == "markdown":
        return generate_markdown(routes)

    # 默认文本格式
    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow API Documentation")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Total endpoints: {len(routes)}")
    lines.append("")

    for route in routes:
        methods = ", ".join(route["methods"])
        lines.append(f"[{methods}] {route['path']}")
        lines.append(f"  Function: {route.get('function', 'unknown')}")
        if route.get("description"):
            lines.append(f"  Description: {route['description']}")
        if route.get("params"):
            lines.append(f"  Parameters: {route['params']}")
        lines.append("")

    if not routes:
        lines.append("[OK] No API routes found!")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow API Documentation Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate docs for single file
  python api-docgen.py --file app.py

  # Generate docs for directory
  python api-docgen.py --dir src/

  # Generate OpenAPI spec
  python api-docgen.py --file app.py --format openapi

  # Generate Markdown docs
  python api-docgen.py --file app.py --format markdown

  # Save to file
  python api-docgen.py --file app.py --output api-docs.json
        """
    )

    parser.add_argument("--dir", "-d", help="Directory to scan")
    parser.add_argument("--file", "-f", help="Single file to analyze")
    parser.add_argument("--format", choices=["text", "json", "openapi", "markdown"], default="text",
                        help="Output format")
    parser.add_argument("--title", default="API Documentation", help="API title (for OpenAPI)")
    parser.add_argument("--version", default="1.0.0", help="API version (for OpenAPI)")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    if not args.dir and not args.file:
        print("Error: --dir or --file is required", file=sys.stderr)
        sys.exit(1)

    # 获取路由
    if args.file:
        routes = analyze_file(args.file)
    else:
        routes = scan_directory(args.dir)

    # 生成文档
    if args.format == "openapi":
        openapi = generate_openapi(routes, args.title, args.version)
        report = json.dumps(openapi, indent=2, ensure_ascii=False)
    else:
        report = format_report(routes, args.format)

    # 输出
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Documentation saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()

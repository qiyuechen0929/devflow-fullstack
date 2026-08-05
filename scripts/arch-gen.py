#!/usr/bin/env python3
"""
DevFlow - Architecture Diagram Generator
从代码生成 Mermaid 架构图
Usage:
  python arch-gen.py --dir src/
  python arch-gen.py --dir src/ --type class
  python arch-gen.py --dir src/ --type flow
  python arch-gen.py --dir src/ --type sequence
  python arch-gen.py --file main.py --type flow
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


def analyze_python_imports(content: str, file_path: str) -> List[Dict]:
    """分析 Python 导入关系"""
    imports = []

    for line in content.split("\n"):
        line = line.strip()

        # import xxx
        match = re.match(r"^import\s+(\w+(?:\.\w+)*)", line)
        if match:
            imports.append({
                "from": file_path,
                "to": match.group(1),
                "type": "import"
            })

        # from xxx import yyy
        match = re.match(r"^from\s+(\w+(?:\.\w+)*)\s+import", line)
        if match:
            imports.append({
                "from": file_path,
                "to": match.group(1),
                "type": "from_import"
            })

    return imports


def analyze_python_classes(content: str, file_path: str) -> List[Dict]:
    """分析 Python 类定义"""
    classes = []
    current_class = None
    methods = []

    for i, line in enumerate(content.split("\n"), 1):
        # 类定义
        match = re.match(r"^class\s+(\w+)(?:\(([^)]*)\))?:", line)
        if match:
            if current_class:
                current_class["methods"] = methods
                classes.append(current_class)

            current_class = {
                "name": match.group(1),
                "file": file_path,
                "line": i,
                "parent": match.group(2) if match.group(2) else None,
                "methods": []
            }
            methods = []

        # 方法定义
        match = re.match(r"^\s+def\s+(\w+)\s*\(([^)]*)\)", line)
        if match and current_class:
            methods.append({
                "name": match.group(1),
                "params": match.group(2)
            })

    if current_class:
        current_class["methods"] = methods
        classes.append(current_class)

    return classes


def analyze_python_functions(content: str, file_path: str) -> List[Dict]:
    """分析 Python 函数定义"""
    functions = []

    for i, line in enumerate(content.split("\n"), 1):
        match = re.match(r"^def\s+(\w+)\s*\(([^)]*)\)", line)
        if match:
            functions.append({
                "name": match.group(1),
                "file": file_path,
                "line": i,
                "params": match.group(2)
            })

    return functions


def analyze_js_imports(content: str, file_path: str) -> List[Dict]:
    """分析 JavaScript/TypeScript 导入关系"""
    imports = []

    for line in content.split("\n"):
        line = line.strip()

        # import xxx from 'yyy'
        match = re.match(r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]", line)
        if match:
            imports.append({
                "from": file_path,
                "to": match.group(1),
                "type": "import"
            })

        # require('xxx')
        match = re.match(r"(?:const|let|var)\s+\w+\s*=\s*require\s*\(['\"]([^'\"]+)['\"]\)", line)
        if match:
            imports.append({
                "from": file_path,
                "to": match.group(1),
                "type": "require"
            })

    return imports


def analyze_js_classes(content: str, file_path: str) -> List[Dict]:
    """分析 JavaScript/TypeScript 类定义"""
    classes = []

    for i, line in enumerate(content.split("\n"), 1):
        match = re.match(r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?", line)
        if match:
            classes.append({
                "name": match.group(1),
                "file": file_path,
                "line": i,
                "parent": match.group(2) if match.group(2) else None,
                "methods": []
            })

    return classes


def scan_directory(directory: str) -> Dict:
    """扫描目录，分析代码结构"""
    dir_path = Path(directory)

    all_imports = []
    all_classes = []
    all_functions = []

    extensions = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript"
    }

    for file_path in dir_path.rglob("*"):
        if any(part.startswith(".") or part in ("node_modules", "vendor", "dist", "build", "__pycache__")
               for part in file_path.parts):
            continue

        if file_path.suffix in extensions and file_path.is_file():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(file_path.relative_to(dir_path))

                if file_path.suffix == ".py":
                    all_imports.extend(analyze_python_imports(content, rel_path))
                    all_classes.extend(analyze_python_classes(content, rel_path))
                    all_functions.extend(analyze_python_functions(content, rel_path))
                else:
                    all_imports.extend(analyze_js_imports(content, rel_path))
                    all_classes.extend(analyze_js_classes(content, rel_path))
            except Exception as e:
                print(f"Error processing {file_path}: {e}", file=sys.stderr)

    return {
        "imports": all_imports,
        "classes": all_classes,
        "functions": all_functions
    }


def generate_dependency_graph(analysis: Dict) -> str:
    """生成依赖关系图"""
    lines = ["graph LR"]

    # 收集所有节点
    nodes = set()
    for imp in analysis["imports"]:
        nodes.add(imp["from"])
        nodes.add(imp["to"])

    # 生成节点ID
    node_ids = {}
    for i, node in enumerate(sorted(nodes)):
        node_ids[node] = f"N{i}"

    # 添加节点
    for node, node_id in node_ids.items():
        label = Path(node).stem if "/" in node or "\\" in node else node
        lines.append(f"    {node_id}[\"{label}\"]")

    # 添加边
    seen_edges = set()
    for imp in analysis["imports"]:
        from_id = node_ids.get(imp["from"])
        to_id = node_ids.get(imp["to"])
        if from_id and to_id:
            edge = f"{from_id}->{to_id}"
            if edge not in seen_edges:
                seen_edges.add(edge)
                lines.append(f"    {from_id} --> {to_id}")

    return "\n".join(lines)


def generate_class_diagram(analysis: Dict) -> str:
    """生成类图"""
    lines = ["classDiagram"]

    for cls in analysis["classes"]:
        class_id = cls["name"]
        lines.append(f"    class {class_id} {{")

        # 添加方法
        for method in cls.get("methods", [])[:10]:  # 限制方法数量
            lines.append(f"        +{method['name']}({method.get('params', '')})")

        lines.append("    }")

        # 继承关系
        if cls.get("parent"):
            lines.append(f"    {cls['parent']} <|-- {class_id}")

    return "\n".join(lines)


def generate_flowchart(analysis: Dict, entry_point: str = None) -> str:
    """生成流程图"""
    lines = ["flowchart TD"]

    # 如果有入口点，分析调用链
    if entry_point:
        lines.append(f"    Start([\"{entry_point}\"])")

        # 简化的调用链分析
        functions_by_file = defaultdict(list)
        for func in analysis["functions"]:
            functions_by_file[func["file"]].append(func)

        # 添加函数节点
        for i, func in enumerate(analysis["functions"][:20]):  # 限制数量
            func_id = f"F{i}"
            lines.append(f"    {func_id}[\"{func['name']}()\"]")

            # 简单的连接逻辑
            if i > 0:
                lines.append(f"    F{i-1} --> {func_id}")

        if analysis["functions"]:
            lines.append(f"    F{len(analysis['functions'])-1} --> End([\"End\"])")
    else:
        # 生成简单的模块关系图
        modules = set()
        for imp in analysis["imports"]:
            modules.add(Path(imp["from"]).stem)
            modules.add(Path(imp["to"]).stem)

        for i, module in enumerate(sorted(modules)[:15]):
            lines.append(f"    M{i}[\"{module}\"]")

        # 添加依赖关系
        seen = set()
        for imp in analysis["imports"][:20]:
            from_mod = Path(imp["from"]).stem
            to_mod = Path(imp["to"]).stem
            if from_mod != to_mod:
                edge = f"{from_mod}->{to_mod}"
                if edge not in seen:
                    seen.add(edge)
                    from_idx = sorted(list(modules)[:15]).index(from_mod) if from_mod in list(modules)[:15] else -1
                    to_idx = sorted(list(modules)[:15]).index(to_mod) if to_mod in list(modules)[:15] else -1
                    if from_idx >= 0 and to_idx >= 0:
                        lines.append(f"    M{from_idx} --> M{to_idx}")

    return "\n".join(lines)


def generate_sequence_diagram(analysis: Dict) -> str:
    """生成时序图"""
    lines = ["sequenceDiagram"]

    # 简化的时序图：展示模块间调用
    modules = []
    for imp in analysis["imports"][:10]:
        from_mod = Path(imp["from"]).stem
        to_mod = Path(imp["to"]).stem
        if from_mod not in modules:
            modules.append(from_mod)
        if to_mod not in modules:
            modules.append(to_mod)

    # 添加参与者
    for module in modules[:8]:
        lines.append(f"    participant {module}")

    # 添加调用关系
    for imp in analysis["imports"][:10]:
        from_mod = Path(imp["from"]).stem
        to_mod = Path(imp["to"]).stem
        if from_mod != to_mod and from_mod in modules and to_mod in modules:
            lines.append(f"    {from_mod}->>+{to_mod}: call")

    return "\n".join(lines)


def format_report(analysis: Dict, diagram_type: str, format: str = "text") -> str:
    """格式化报告"""
    if format == "json":
        return json.dumps({
            "type": diagram_type,
            "imports": len(analysis["imports"]),
            "classes": len(analysis["classes"]),
            "functions": len(analysis["functions"]),
            "diagram": generate_diagram(analysis, diagram_type)
        }, indent=2, ensure_ascii=False)

    lines = []
    lines.append("=" * 60)
    lines.append("DevFlow Architecture Diagram Generator")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"[Analysis]")
    lines.append(f"  Imports:  {len(analysis['imports'])}")
    lines.append(f"  Classes:  {len(analysis['classes'])}")
    lines.append(f"  Functions: {len(analysis['functions'])}")
    lines.append("")

    diagram = generate_diagram(analysis, diagram_type)

    lines.append(f"[Mermaid Diagram - {diagram_type}]")
    lines.append("-" * 60)
    lines.append("```mermaid")
    lines.append(diagram)
    lines.append("```")
    lines.append("-" * 60)
    lines.append("")
    lines.append("Copy the above Mermaid code to render the diagram.")
    lines.append("Online renderer: https://mermaid.live")
    lines.append("=" * 60)

    return "\n".join(lines)


def generate_diagram(analysis: Dict, diagram_type: str) -> str:
    """根据类型生成图表"""
    if diagram_type == "dependency":
        return generate_dependency_graph(analysis)
    elif diagram_type == "class":
        return generate_class_diagram(analysis)
    elif diagram_type == "flow":
        return generate_flowchart(analysis)
    elif diagram_type == "sequence":
        return generate_sequence_diagram(analysis)
    else:
        return generate_dependency_graph(analysis)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Architecture Diagram Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate dependency graph
  python arch-gen.py --dir src/

  # Generate class diagram
  python arch-gen.py --dir src/ --type class

  # Generate flowchart
  python arch-gen.py --dir src/ --type flow

  # Generate sequence diagram
  python arch-gen.py --dir src/ --type sequence

  # Generate from single file
  python arch-gen.py --file main.py --type flow

  # Output as JSON
  python arch-gen.py --dir src/ --format json
        """
    )

    parser.add_argument("--dir", "-d", help="Project directory")
    parser.add_argument("--file", "-f", help="Single file to analyze")
    parser.add_argument("--type", "-t", choices=["dependency", "class", "flow", "sequence"],
                        default="dependency", help="Diagram type")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    if not args.dir and not args.file:
        print("Error: --dir or --file is required", file=sys.stderr)
        sys.exit(1)

    # 分析代码
    if args.file:
        content = Path(args.file).read_text(encoding="utf-8", errors="ignore")
        ext = Path(args.file).suffix

        analysis = {"imports": [], "classes": [], "functions": []}

        if ext == ".py":
            analysis["imports"] = analyze_python_imports(content, args.file)
            analysis["classes"] = analyze_python_classes(content, args.file)
            analysis["functions"] = analyze_python_functions(content, args.file)
        else:
            analysis["imports"] = analyze_js_imports(content, args.file)
            analysis["classes"] = analyze_js_classes(content, args.file)
    else:
        analysis = scan_directory(args.dir)

    # 生成报告
    report = format_report(analysis, args.type, args.format)

    # 输出
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()

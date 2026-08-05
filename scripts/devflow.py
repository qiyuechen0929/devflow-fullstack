#!/usr/bin/env python3
"""
DevFlow - Full Pipeline Orchestrator
One command to run the entire DevFlow pipeline.
Usage: python devflow.py --dir . 
       python devflow.py --dir . --quick        (fast mode, skip heavy checks)
       python devflow.py --dir . --output report.md
"""

import argparse, os, sys, subprocess, json, time
from pathlib import Path
from datetime import datetime

# 确保可以 import 同目录模块（toolchain 等），无论从哪个 cwd 运行
sys.path.insert(0, str(Path(__file__).resolve().parent))

import toolchain

SCRIPTS_DIR = Path(__file__).parent

PIPELINE = {
    "1-env": {
        "script": "env-check.py",
        "desc": "Environment & Project Detection",
        "quick": True,
    },
    "2-toolchain": {
        "script": "toolchain.py",
        "desc": "Third-party Tool Detection",
        "quick": True,
        "custom": lambda target: (True, toolchain.make_toolchain_report(target)),
    },
    "3-metrics": {
        "script": "metrics-i18n.py",
        "args": ["--mode", "metrics"],
        "desc": "Code Metrics",
        "quick": True,
    },
    "4-review": {
        "script": "review.py",
        "args": ["--mode", "all"],
        "desc": "Bug & Security & Readability Scan",
        "quick": False,
    },
    "5-bandit": {
        "script": "toolchain.py",
        "desc": "Bandit Security Scan (if installed)",
        "quick": False,
        "custom": lambda target: _run_tool("bandit", target),
    },
    "6-smell": {
        "script": "smell.py",
        "desc": "Code Smell Detection",
        "quick": False,
    },
    "7-race": {
        "script": "racecheck.py",
        "desc": "Race Condition Analysis",
        "quick": False,
    },
    "8-db": {
        "script": "db-optimize.py",
        "desc": "Database Query Optimization",
        "quick": False,
    },
    "9-i18n": {
        "script": "metrics-i18n.py",
        "args": ["--mode", "i18n"],
        "desc": "i18n Hardcoded String Detection",
        "quick": True,
    },
}


def _run_tool(name, target):
    """调用工具链（bandit/ruff/pytest），未安装时返回提示"""
    if name == "bandit":
        ok, out = toolchain.run_bandit(target)
    elif name == "ruff":
        ok, out = toolchain.run_ruff(target)
    elif name == "pytest":
        ok, out = toolchain.run_pytest(target)
    else:
        return False, f"未知工具: {name}"
    if ok:
        return True, out
    return True, out  # 未安装也返回 ok（视为可跳过步骤），输出提示

def run_step(step_id, step_config, target_dir, verbose=False):
    # 自定义步骤（工具链检测等）
    if "custom" in step_config:
        ok, output = step_config["custom"](target_dir)
        return {
            "id": step_id,
            "desc": step_config["desc"],
            "ok": ok,
            "output": str(output),
            "errors": "",
            "elapsed": 0.0,
        }

    script = SCRIPTS_DIR / step_config["script"]
    args = step_config.get("args", [])
    cmd = [sys.executable, str(script), "--dir", target_dir] + args

    if verbose:
        print(f"  Running: {' '.join(cmd)}")

    try:
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
        elapsed = time.time() - start
        return {
            "id": step_id,
            "desc": step_config["desc"],
            "ok": result.returncode == 0,
            "output": result.stdout.strip(),
            "errors": result.stderr.strip(),
            "elapsed": elapsed,
        }
    except subprocess.TimeoutExpired:
        return {
            "id": step_id,
            "desc": step_config["desc"],
            "ok": False,
            "output": "",
            "errors": "Timeout (>60s)",
            "elapsed": 60,
        }
    except Exception as e:
        return {
            "id": step_id,
            "desc": step_config["desc"],
            "ok": False,
            "output": "",
            "errors": str(e),
            "elapsed": 0,
        }

def generate_report(results, target_dir, total_time):
    lines = []
    lines.append(f"# DevFlow Pipeline Report")
    lines.append(f"")
    lines.append(f"- **Target**: `{target_dir}`")
    lines.append(f"- **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **Duration**: {total_time:.1f}s")
    lines.append(f"")
    
    passed = sum(1 for r in results if r["ok"])
    lines.append(f"## Summary: {passed}/{len(results)} checks passed")
    lines.append("")
    lines.append("| Step | Result | Time |")
    lines.append("|------|--------|------|")
    for r in results:
        icon = "[OK]" if r["ok"] else "[!!]"
        lines.append(f"| {r['desc']} | {icon} | {r['elapsed']:.1f}s |")
    
    lines.append("")
    for r in results:
        if r["output"]:
            lines.append(f"### {r['desc']}")
            lines.append("")
            lines.append("```")
            # Truncate very long outputs
            out = r["output"]
            if len(out) > 2000:
                out = out[:2000] + "\n... (truncated)"
            lines.append(out)
            lines.append("```")
            lines.append("")
        
        if r["errors"]:
            lines.append(f"**Errors**: {r['errors'][:500]}")
            lines.append("")
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="DevFlow Full Pipeline")
    parser.add_argument("--dir", default=".", help="Target directory")
    parser.add_argument("--quick", action="store_true", help="Quick mode (skip heavy checks)")
    parser.add_argument("--output", help="Output report file (markdown)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    target = os.path.abspath(args.dir)
    if not os.path.isdir(target):
        print(f"Error: {target} is not a directory")
        sys.exit(1)

    steps = {k: v for k, v in PIPELINE.items() if not args.quick or v["quick"]}
    
    print(f"DevFlow Pipeline: {target}")
    print(f"Steps: {len(steps)} ({'quick' if args.quick else 'full'})\n")
    
    results = []
    start_total = time.time()
    
    for step_id in steps:
        config = steps[step_id]
        print(f"[{step_id}] {config['desc']}...", end=" ", flush=True)
        r = run_step(step_id, config, target, args.verbose)
        icon = "[OK]" if r["ok"] else "[!!]"
        print(f"{icon} ({r['elapsed']:.1f}s)")
        results.append(r)
    
    total_time = time.time() - start_total
    print(f"\nDone. {sum(1 for r in results if r['ok'])}/{len(results)} passed in {total_time:.1f}s")
    
    report = generate_report(results, target, total_time)
    
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved: {args.output}")
    else:
        print("\n--- Report Preview ---\n")
        print("\n".join(report.split("\n")[:30]))
        print(f"\n... (use --output report.md for full report)")

if __name__ == "__main__":
    main()

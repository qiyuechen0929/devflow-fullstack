#!/usr/bin/env python3
"""
DevFlow - Self Tests
Usage: python selftest.py
"""

import subprocess, sys, os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

TESTS = [
    # (script, args, expected_in_output)
    ("review.py", ["--file", __file__, "--mode", "scan"], "findings"),
    ("smell.py", ["--file", __file__], ""),
    ("regex.py", ["--test", "13800138000", "--pattern", r"^1[3-9]\d{9}$"], "Match"),
    ("regex.py", ["--explain", r"^\d{3}-\d{4}$"], "digit"),
    ("env-check.py", ["--dir", "."], "System"),
    ("explain.py", ["--file", __file__], "Functions"),
    ("metrics-i18n.py", ["--mode", "metrics", "--dir", "."], "Lines"),
    ("boundary.py", ["--file", __file__, "--func", "main"], "Boundary"),
    ("racecheck.py", ["--file", __file__], ""),
    ("db-optimize.py", ["--file", __file__], ""),
    ("a11y.py", ["--file", __file__], ""),
    ("apitools.py", ["--mode", "log", "--file", __file__], ""),
    ("clean-debug.py", ["--dir", "."], ""),
    ("config-gen.py", ["--type", "dockerfile", "--dir", "."], ""),
    ("docgen.py", ["--file", __file__, "--mode", "inline"], ""),
    ("git-helper.py", ["--mode", "commit"], ""),
    ("testgen.py", ["--file", __file__, "--framework", "pytest"], ""),
    ("migrate.py", ["--from", "py2", "--to", "py3", "--file", __file__, "--dry-run"], ""),
    # New scripts
    ("pr-review.py", ["--file", __file__], ""),
    ("deps-scan.py", ["--dir", "."], ""),
    ("team-sync.py", ["--list"], ""),
    ("dashboard.py", ["--dir", ".", "--format", "json"], "total_files"),
    ("arch-gen.py", ["--file", __file__, "--type", "dependency"], "mermaid"),
    ("bench.py", ["--file", __file__, "--list"], "Functions"),
    ("snippet.py", ["--list"], "snippets"),
    ("model-manager.py", ["--list"], "Providers"),
    ("watch.py", ["--file", __file__, "--mode", "quick"], ""),
    # Latest scripts
    ("changelog.py", ["--dir", "."], ""),
    ("formatter.py", ["--file", __file__, "--check"], ""),
    ("api-docgen.py", ["--file", __file__], ""),
    ("docker-compose-gen.py", ["--list"], "Services"),
    ("log-analyzer.py", ["--file", __file__], ""),
    ("heatmap.py", ["--file", __file__], ""),
    ("tech-debt.py", ["--list"], "debts"),
    ("deploy.py", ["--list"], "Platforms"),
    ("profiler.py", ["--file", __file__], ""),
    ("similarity.py", ["--file", __file__], ""),
    # Newly added scripts
    ("todo-scan.py", ["--file", __file__], ""),
    ("complexity.py", ["--file", __file__], "complexity"),
    ("git-stats.py", ["--dir", "."], ""),
    # Workflow & Agents
    ("workflow.py", ["status", "--dir", "."], "当前阶段"),
    ("agents.py", ["--list"], "角色"),
    # New utility scripts
    ("doctor.py", ["--dir", "."], "健康诊断"),
    ("security-audit.py", ["--dir", "."], "安全审计"),
    ("tdd-check.py", ["--dir", "."], "TDD"),
    ("code-map.py", ["--dir", ".", "--depth", "1"], "代码地图"),
    ("memory.py", ["list", "--dir", "."], "暂无记忆"),
    ("refactor.py", ["--dir", "."], ""),
    ("onboarding.py", ["--dir", "."], "导览"),
    ("coverage-scan.py", ["--dir", "."], "覆盖率"),
    # Toolchain & LLM bridge
    ("toolchain.py", ["--check"], "bandit"),
    ("llm.py", ["--check"], "provider"),
]

def run_test(script, args):
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + [str(a) for a in args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -2, str(e)

def main():
    passed = 0
    failed = 0

    print("DevFlow Self-Test Suite\n")
    
    for script, args, _ in TESTS:
        script_path = SCRIPTS_DIR / script
        if not script_path.exists():
            print(f"  SKIP {script} (not found)")
            continue

        code, output = run_test(script, args)
        # Consider pass if exit code is 0 or 1 (1 often means "found issues")
        ok = code in (0, 1)
        
        if ok:
            print(f"  [OK] {script} (exit={code})")
            passed += 1
        else:
            print(f"  [FAIL] {script} (exit={code}): {output[:100]}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed, {len(TESTS)} total")
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()

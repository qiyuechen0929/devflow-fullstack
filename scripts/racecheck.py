#!/usr/bin/env python3
"""
DevFlow - Race Condition & Concurrency Analyzer (#15)
Usage: python racecheck.py --file foo.py
"""

import argparse, os, re
from pathlib import Path

LANG_PATTERNS = {
    "python": {
        "shared_var": r"(?:global|nonlocal)\s+(\w+)",
        "thread": r"threading\.Thread|concurrent\.futures|asyncio\.create_task",
        "lock": r"threading\.Lock|asyncio\.Lock|with.*lock",
        "unsafe": r"\.append\(|\.remove\(|dict\[.*\]\s*=",
    },
    "javascript": {
        "shared_var": r"(?:let|var)\s+(\w+)\s*=.*\n.*(?:\bawait\b|\bthen\b|Promise\.all)",
        "thread": r"Promise\.all|Promise\.race|async\s+function|\.then\(",
        "lock": r"Mutex|Semaphore",
        "unsafe": r"\.push\(|\.splice\(|\w+\s*=\s*\w+\s*\+\+",
    },
    "java": {
        "shared_var": r"(?:static|volatile)\s+\w+\s+(\w+)",
        "thread": r"new\s+Thread|ExecutorService|Runnable|CompletableFuture",
        "lock": r"synchronized|ReentrantLock|AtomicInteger|volatile",
        "unsafe": r"\.add\(|\.put\(|\+\+|\-\-",
    },
    "go": {
        "shared_var": r"var\s+(\w+)\s+\w+",
        "thread": r"go\s+func|go\s+\w+\(",
        "lock": r"sync\.Mutex|sync\.RWMutex|sync\.Once",
        "unsafe": r"\w+\+\+|\w+\-\-|append\(|map\[",
    },
}

def detect_lang(filepath):
    ext = Path(filepath).suffix
    return {".py":"python",".js":"javascript",".ts":"javascript",
            ".tsx":"javascript",".jsx":"javascript",".java":"java",
            ".go":"go"}.get(ext)

def analyze_file(filepath):
    lang = detect_lang(filepath)
    if not lang: return []
    
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")
        patterns = LANG_PATTERNS[lang]
        results = []
        has_threads = False
        has_lock = False
        shared_vars = []
        unsafe_ops = []

        for i, line in enumerate(lines, 1):
            if re.search(patterns["thread"], line):
                has_threads = True
            if re.search(patterns["lock"], line):
                has_lock = True
            m = re.search(patterns["shared_var"], line)
            if m:
                shared_vars.append((i, m.group(1)))
            if re.search(patterns["unsafe"], line):
                unsafe_ops.append(i)

        if has_threads and not has_lock:
            results.append(f"[!!] {filepath} - 检测到并发代码但无锁保护")
        
        if shared_vars and has_threads and not has_lock:
            for line_no, var in shared_vars:
                results.append(f"[!] {filepath}:{line_no} - 共享变量 `{var}` 无并发保护")

        if unsafe_ops and has_threads:
            for line_no in unsafe_ops[:3]:
                results.append(f"[*] {filepath}:{line_no} - 非原子操作，多线程下可能出错")

        return results
    except Exception:
        return []

def main():
    parser = argparse.ArgumentParser(description="Race Condition Analyzer")
    parser.add_argument("--file")
    parser.add_argument("--dir", default=".")
    args = parser.parse_args()

    exts = {".py",".js",".ts",".tsx",".jsx",".java",".go"}
    ignore = {"node_modules",".git","dist","build","__pycache__",".next"}

    all_results = []
    targets = [args.file] if args.file else []
    if not args.file:
        for root, dirs, files in os.walk(args.dir):
            dirs[:] = [d for d in dirs if d not in ignore]
            for f in files:
                if Path(f).suffix in exts:
                    targets.append(os.path.join(root, f))

    for t in targets:
        all_results.extend(analyze_file(t))

    if all_results:
        print(f"发现 {len(all_results)} 个并发安全问题:\n")
        for r in all_results:
            print(r)
    else:
        print("未发现明显并发问题 [OK]")

if __name__ == "__main__":
    main()

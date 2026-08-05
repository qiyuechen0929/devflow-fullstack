#!/usr/bin/env python3
"""
DevFlow Fullstack - 一键安装器

将 DevFlow 工具链接入你的项目，支持多种 AI 编程平台：

    python setup.py install             # 全部平台接入
    python setup.py install --platform claude
    python setup.py install --platform codex
    python setup.py install --platform opencode
    python setup.py install --platform cursor,windsurf

支持的平台：claude, codex, opencode, cursor, windsurf, trae, copilot

零第三方依赖，只需 Python 3.10+。
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parent

# 平台 → (需要复制的源文件/目录, 目标相对路径)
PLATFORM_FILES = {
    "claude": [
        (".claude/commands", ".claude/commands"),
        (".claude/hooks", ".claude/hooks"),
        (".claude/settings.json", ".claude/settings.json"),
        ("CLAUDE.md", "CLAUDE.md"),
        ("scripts", "scripts"),
    ],
    "codex": [
        ("skills/devflow-fullstack", ".agents/skills/devflow-fullstack"),
        ("skills/devflow-fullstack", "skills/devflow-fullstack"),
        ("agents", "agents"),
        ("scripts", "scripts"),
    ],
    "opencode": [
        ("opencode.json", "opencode.json"),
        ("scripts", "scripts"),
    ],
    "cursor": [
        (".cursorrules", ".cursorrules"),
        ("scripts", "scripts"),
    ],
    "windsurf": [
        (".windsurfrules", ".windsurfrules"),
        ("scripts", "scripts"),
    ],
    "trae": [
        (".trae/rules", ".trae/rules"),
        ("scripts", "scripts"),
    ],
    "copilot": [
        (".github/copilot-instructions.md", ".github/copilot-instructions.md"),
        ("scripts", "scripts"),
    ],
}

# 全局安装：目标为 HOME 下的固定位置（codex/claude skill 自包含，含 scripts）
GLOBAL_FILES = {
    "claude": [
        (".claude/commands", "commands"),
        ("skills/devflow-fullstack", "skills/devflow-fullstack"),
        ("scripts", "skills/devflow-fullstack/scripts"),
    ],
    "codex": [
        ("skills/devflow-fullstack", ".codex/skills/devflow-fullstack"),
        ("scripts", ".codex/skills/devflow-fullstack/scripts"),
    ],
}


def install_global(platform: str, home_dir: Path, force: bool):
    """全局安装（到用户 HOME，用于 claude 全局命令、codex skill 等）"""
    entries = GLOBAL_FILES.get(platform)
    if not entries:
        return 0
    n = 0
    for src_rel, dst_rel in entries:
        src = SOURCE_DIR / src_rel
        dst = home_dir / dst_rel
        n += copy_tree(src, dst, force)
    return n

# scripts 目录下的文件在重复复制时去重
COPIED_SCRIPTS = set()


def copy_tree(src: Path, dst: Path, force: bool):
    """复制目录/文件到目标，跳过已存在的（除非 force）"""
    if not src.exists():
        return 0

    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for item in src.iterdir():
            if item.is_dir():
                n += copy_tree(item, dst / item.name, force)
            else:
                n += copy_file(item, dst / item.name, force)
        return n

    return copy_file(src, dst, force)


def copy_file(src: Path, dst: Path, force: bool):
    """复制单个文件"""
    if dst.exists() and not force:
        return 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return 1


def install_platform(platform: str, target_dir: Path, force: bool):
    """安装单个平台"""
    entries = PLATFORM_FILES.get(platform)
    if not entries:
        print(f"  未知平台: {platform}")
        return 0

    n = 0
    for src_rel, dst_rel in entries:
        src = SOURCE_DIR / src_rel
        dst = target_dir / dst_rel
        n += copy_tree(src, dst, force)
    return n


def verify_install(target_dir: Path):
    """验证安装结果"""
    ok = True
    checks = [
        ("scripts/review.py", "review.py"),
        ("scripts/selftest.py", "selftest.py"),
    ]
    for rel, name in checks:
        p = target_dir / rel
        if p.exists():
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} 缺失")
            ok = False
    return ok


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Fullstack 一键安装器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n  python setup.py install\n  python setup.py install --platform claude,codex\n  python setup.py install --force",
    )
    sub = parser.add_subparsers(dest="command")

    install_p = sub.add_parser("install", help="安装到目标项目")
    install_p.add_argument("--platform", "-p",
                           help="平台列表（逗号分隔），默认全部")
    install_p.add_argument("--target", "-t", default=".",
                           help="目标项目目录（默认当前目录）")
    install_p.add_argument("--force", "-f", action="store_true",
                           help="覆盖已存在的文件")
    install_p.add_argument("--global", "-g", dest="global_install", action="store_true",
                           help="全局安装（claude 命令、codex skill 到 HOME）")
    install_p.add_argument("--list", action="store_true",
                           help="列出支持的平台")

    args = parser.parse_args()

    if args.command != "install":
        parser.print_help()
        return

    if args.list:
        print("支持的平台：")
        for p in PLATFORM_FILES:
            print(f"  - {p}")
        return

    target_dir = Path(args.target).resolve()
    if not target_dir.is_dir():
        print(f"错误: 目标目录不存在: {target_dir}")
        sys.exit(1)

    platforms = args.platform.split(",") if args.platform else list(PLATFORM_FILES.keys())
    platforms = [p.strip() for p in platforms if p.strip()]

    # 全局安装模式
    if args.global_install:
        home_dir = Path.home()
        print(f"🌍 全局安装到: {home_dir}")
        print(f"   平台: {', '.join(platforms)}\n")
        total = 0
        for p in platforms:
            n = install_global(p, home_dir, args.force)
            total += n
            print(f"  {p:<10} 已接入 ({n} 个文件)")
        print(f"\n✅ 全局安装完成，共复制 {total} 个文件")
        if "codex" in platforms:
            print("  • Codex skill 已安装到 ~/.codex/skills/devflow-fullstack/")
        if "claude" in platforms:
            print("  • Claude 全局命令已安装到 ~/.claude/commands/")
        return

    # 防止装到 DevFlow 自己
    if target_dir == SOURCE_DIR:
        print("提示: 检测到目标就是 DevFlow 仓库本身，跳过安装（已内置全部配置）。")
        print("请在其他项目中运行: python <devflow路径>/setup.py install")
        sys.exit(0)

    print(f"📦 DevFlow 安装到: {target_dir}")
    print(f"   平台: {', '.join(platforms)}\n")

    total = 0
    for p in platforms:
        n = install_platform(p, target_dir, args.force)
        total += n
        print(f"  {p:<10} 已接入 ({n} 个文件)")

    print(f"\n✅ 完成，共复制 {total} 个文件")

    # 验证
    if "claude" in platforms or "codex" in platforms or "opencode" in platforms:
        print("\n验证核心脚本:")
        verify_install(target_dir)

    print("\n下一步：")
    if "claude" in platforms:
        print("  • Claude Code: 打开项目后输入 /devflow-review 试试")
    if "codex" in platforms:
        print("  • Codex: 运行 `python setup.py install --global --platform codex` 安装全局 skill")
    if "opencode" in platforms:
        print("  • opencode: 在 opencode 中打开项目即可加载配置")
    print("  • 运行自测: python scripts/selftest.py")


def _delegate_to_setuptools():
    """当 pip/构建工具用 setuptools 命令调用 setup.py 时，委托给 setuptools。"""
    try:
        from setuptools import setup
    except ImportError:
        # 无 setuptools：仅支持 DevFlow 安装器用法
        return False

    # 用 setuptools 读取 pyproject.toml 中的元数据
    try:
        setup()
        return True
    except SystemExit:
        return True
    except Exception:
        # setuptools 不适用时退回 DevFlow 安装器
        return False


if __name__ == "__main__":
    # pip 构建时用 setuptools 命令调用（egg_info/build/sdist/bdist_wheel 等）
    _SETUPTOOLS_CMDS = {"egg_info", "build", "sdist", "bdist_wheel", "bdist", "install_egg_info",
                        "develop", "build_py", "build_ext", "install_lib", "install_scripts",
                        "dist_info", "metadata", "version"}
    _first_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if _first_arg in _SETUPTOOLS_CMDS:
        if _delegate_to_setuptools():
            sys.exit(0)
    # DevFlow 安装器
    main()

#!/usr/bin/env bash
# ============================================================
# DevFlow Fullstack - 一条命令接入你的项目
#
# 用法（在你的项目根目录执行）：
#   方式 1（推荐，克隆后）：
#     python setup.py install
#
#   方式 2（从 GitHub 直接拉取，需要 git）：
#     curl -fsSL https://raw.githubusercontent.com/qiyuechen0929/devflow-fullstack/main/install.sh | bash
#
#   方式 3（指定平台）：
#     python setup.py install --platform claude,codex,opencode
#
# 支持的平台：claude / codex / opencode / cursor / windsurf / trae / copilot
# ============================================================

set -euo pipefail

echo "📦 DevFlow Fullstack 安装器"
echo "==========================="

# 检测 Python
PYTHON=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        VERSION=$("$cand" -c 'import sys; print(sys.version_info[0], sys.version_info[1])' 2>/dev/null || true)
        MAJOR=${VERSION%% *}
        if [ "$MAJOR" = "3" ]; then
            PYTHON="$cand"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ 未找到 Python 3，请先安装 Python 3.10+"
    exit 1
fi
echo "✅ 使用 Python: $($PYTHON --version 2>&1)"

# 定位 DevFlow 目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_PY=""
if [ -f "$SCRIPT_DIR/setup.py" ]; then
    SETUP_PY="$SCRIPT_DIR/setup.py"
elif command -v devflow >/dev/null 2>&1; then
    # devflow 已通过 pip 安装，用 devflow setup 命令
    SETUP_PY=""
else
    echo "❌ 找不到 setup.py。请先克隆仓库，或确保 devflow 命令可用。"
    exit 1
fi

# 如果 setup.py 不存在但 devflow 命令存在
if [ -z "$SETUP_PY" ]; then
    devflow setup install "$@"
    exit $?
fi

# 平台参数
PLATFORM=""
GLOBAL=""
if [ $# -ge 2 ] && [ "$1" = "--platform" ]; then
    PLATFORM="--platform $2"
    shift 2
fi
if [ $# -ge 1 ] && [ "$1" = "--global" ]; then
    GLOBAL="--global"
    shift 1
fi

# 目标目录
TARGET="."
if [ $# -ge 2 ] && [ "$1" = "--target" ]; then
    TARGET="$2"
    shift 2
fi

echo "📍 目标项目: $TARGET"
echo "  平台: ${PLATFORM:-全部}"
[ -n "$GLOBAL" ] && echo "  模式: 全局安装 (HOME)"

# 执行安装
if [ -n "$GLOBAL" ]; then
    $PYTHON "$SETUP_PY" install $PLATFORM --global
else
    $PYTHON "$SETUP_PY" install $PLATFORM --target "$TARGET"
fi

echo ""
echo "🎉 安装完成！"
echo "  运行自测: $PYTHON $TARGET/scripts/selftest.py"

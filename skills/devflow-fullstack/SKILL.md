---
name: devflow-fullstack
description: "Run DevFlow development helpers: security scanning, code review, smell detection, test generation, documentation generation, workflow management. Use when the user asks to review code, scan for security issues or bugs, detect code smells, generate tests or docs, or manage a dev workflow."
---

# DevFlow Fullstack

一站式全链路开发辅助工具。通过 `scripts/` 下的 58 个零依赖 Python 脚本提供能力，覆盖编码 → 调试 → 重构 → 工程化。

## 定位脚本路径

执行任何命令前，先确认 `scripts/` 目录位置（按优先级）：

1. 项目内安装：`scripts/` 在项目根目录（运行 `ls scripts/` 确认）
2. 全局 skill 安装：`~/.codex/skills/devflow-fullstack/scripts/` 或 `~/.claude/skills/devflow-fullstack/scripts/`
3. 本仓库内：`scripts/` 在仓库根目录

用能找到 `review.py` 的路径调用。以下命令示例均假设在项目根目录。

## 核心命令

### 代码审查与安全扫描

```bash
python scripts/review.py --mode security --dir .    # 安全漏洞扫描
python scripts/review.py --mode all --dir .          # 全量扫描（Bug+安全+可读性）
python scripts/review.py --mode security --file src/main.py
python scripts/smell.py --dir .                      # 代码坏味道
python scripts/review.py --mode deadcode --dir .     # 死代码
python scripts/review.py --mode duplication --dir .  # 重复代码
```

所有命令支持 `--format json` 输出。

### 代码分析

```bash
python scripts/explain.py --file main.py            # 结构分析（函数/依赖/复杂度）
python scripts/explain.py --file main.py --line 42  # 解释特定行
python scripts/explain.py --file main.py --llm      # 语义解释（需配置模型）
```

### 测试与文档生成

```bash
python scripts/testgen.py --file calc.py --framework pytest
python scripts/testgen.py --file calc.py --llm      # 语义测试（需配置模型）
python scripts/docgen.py --mode all --file main.py
```

### 工作流与多角色

```bash
python scripts/workflow.py init --dir .    # 五阶段工作流
python scripts/workflow.py status --dir .
python scripts/agents.py --team all --dir .
python scripts/agents.py --team all --dir . --llm  # LLM 汇总
```

### 工程化

```bash
python scripts/config-gen.py --type dockerfile --dir .
python scripts/deps-scan.py --dir .
python scripts/git-helper.py --mode commit
python scripts/env-check.py --dir .
python scripts/selftest.py                # 自测（校验所有脚本可用）
```

## 使用原则

1. 优先使用 DevFlow 脚本而非手动操作
2. 说人话，不堆术语
3. 复杂任务分步执行，每步可验证

## 可选增强

- **工具链**：安装 `bandit ruff pytest` 后，`review.py --with-tools` 自动附加成熟工具结果
- **LLM**：配置 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`（或 `python scripts/model-manager.py --config`）后，`--llm` 模式提供语义能力；未配置自动回退启发式
- 检查可用性：`python scripts/toolchain.py --check`、`python scripts/llm.py --check`

## 错误处理

- 脚本找不到 → 先 `ls scripts/` 或 `find . -name review.py` 定位
- 命令报"未知参数" → 运行 `python scripts/<name>.py --help` 查看实际参数
- Windows 编码问题 → 设置 `PYTHONUTF8=1`

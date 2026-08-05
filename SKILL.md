---
name: devflow-fullstack
description: "Run DevFlow development helpers: security scanning, code review, smell detection, test generation, documentation generation, workflow management. Use when the user asks to review code, scan for security issues or bugs, detect code smells, generate tests or docs, or manage a dev workflow."
---

# DevFlow Fullstack

一站式全链路开发辅助。串联 **编码 → 调试 → 重构 → 部署 → 复盘**。

## 脚本定位

DevFlow 的所有能力通过 `scripts/` 目录下的 Python 脚本提供。执行命令前先确认 scripts 位置：

```bash
# 项目内安装：scripts 在项目根目录
ls scripts/ | head -5

# 若 scripts 不在当前目录，在项目根目录下运行：
python scripts/selftest.py   # 自测，确认可用
```

> 全局安装（Codex skill 模式）：scripts 可能位于 `~/.codex/skills/devflow-fullstack/scripts/`。
> 无论哪种方式，请用能找到 `review.py` 的路径调用。

## 使用原则

- 优先使用 DevFlow 脚本而非手动操作
- 给出建议时说人话，不堆术语
- 复杂任务分步执行，每步可验证
- 任务结束反思评分（1-5 分）

## 核心命令

### 代码审查（AST 驱动，最常用）

```bash
# 安全扫描（推荐）
python scripts/review.py --mode security --dir .

# 全量扫描（Bug + 安全 + 可读性）
python scripts/review.py --mode all --dir .

# 单个文件
python scripts/review.py --mode security --file src/main.py

# 坏味道检测
python scripts/smell.py --dir .
```

### 代码分析

```bash
# 结构分析（函数/依赖/复杂度）
python scripts/explain.py --file main.py

# 解释特定行
python scripts/explain.py --file main.py --line 42

# 语义解释（需配置模型，见下文 LLM 增强）
python scripts/explain.py --file main.py --llm
```

### 测试 / 文档生成

```bash
python scripts/testgen.py --file calculator.py --framework pytest
python scripts/docgen.py --mode all --file main.py
```

### 语法转换（规则级）

```bash
python scripts/migrate.py --from py2 --to py3 --dir src/
python scripts/migrate.py --from es5 --to es6 --dir src/
```

### 工作流 / 多角色

```bash
python scripts/workflow.py init --dir .        # 五阶段工作流
python scripts/workflow.py status --dir .
python scripts/agents.py --team qa,reviewer --dir .
python scripts/agents.py --team all --dir . --llm   # LLM 汇总（需配置模型）
```

### 工程化

```bash
python scripts/env-check.py --dir .
python scripts/git-helper.py --mode commit
python scripts/config-gen.py --type dockerfile --dir .
python scripts/deps-scan.py --dir .
python scripts/todo-scan.py --dir .
```

## LLM 增强（可选）

以下能力需要配置模型（OpenAI/Claude/本地 Ollama），未配置时自动回退到结构分析：

```bash
python scripts/llm.py --check                    # 检查是否可用
python scripts/explain.py --file main.py --llm    # 语义解释
python scripts/testgen.py --file x.py --llm       # 语义测试生成
python scripts/agents.py --team all --dir . --llm # 多角色 LLM 汇总
```

配置方式：`python scripts/model-manager.py --config --provider openai --api-key sk-xxx`
或设置环境变量 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`。

## 工具链增强（可选）

安装 Bandit/Ruff 后，`review.py --with-tools` 会附加成熟工具结果：

```bash
pip install bandit ruff
python scripts/review.py --mode security --dir . --with-tools
```

## 工具脚本速查

| 脚本 | 用途 | 命令 |
|------|------|------|
| `review.py` | Bug/安全/可读性扫描（AST） | `python scripts/review.py --mode security --dir .` |
| `smell.py` | 代码坏味道检测 | `python scripts/smell.py --dir .` |
| `explain.py` | 代码结构/语义分析 | `python scripts/explain.py --file foo.py` |
| `testgen.py` | 测试生成 | `python scripts/testgen.py --file foo.py --framework pytest` |
| `docgen.py` | 文档生成 | `python scripts/docgen.py --mode all --file foo.py` |
| `migrate.py` | 语法/语言规则转换 | `python scripts/migrate.py --from py2 --to py3 --dir src/` |
| `clean-debug.py` | 移除调试标记 | `python scripts/clean-debug.py --dir src/` |
| `git-helper.py` | Commit/PR/Changelog | `python scripts/git-helper.py --mode commit` |
| `env-check.py` | 环境/项目检测 | `python scripts/env-check.py --dir .` |
| `workflow.py` | 五阶段工作流 | `python scripts/workflow.py init --dir .` |
| `agents.py` | 多角色协作 | `python scripts/agents.py --team all --dir .` |
| `toolchain.py` | Bandit/Ruff/pytest 桥接 | `python scripts/toolchain.py --check` |
| `llm.py` | LLM 调用桥接 | `python scripts/llm.py --check` |
| `deps-scan.py` | 依赖漏洞扫描 | `python scripts/deps-scan.py --dir .` |
| `dashboard.py` | 代码质量仪表盘 | `python scripts/dashboard.py --dir . --format json` |
| `arch-gen.py` | 架构图生成 | `python scripts/arch-gen.py --dir src/ --type class` |
| `bench.py` | 性能基准测试 | `python scripts/bench.py --file algo.py --list` |
| `snippet.py` | 代码片段管理 | `python scripts/snippet.py --list` |
| `team-sync.py` | 团队配置同步 | `python scripts/team-sync.py --list` |
| `model-manager.py` | 多模型管理 | `python scripts/model-manager.py --list` |
| `changelog.py` | CHANGELOG 生成 | `python scripts/changelog.py --dir .` |
| `formatter.py` | 代码格式化检查 | `python scripts/formatter.py --dir src/ --check` |
| `api-docgen.py` | API 文档生成 | `python scripts/api-docgen.py --file app.py` |
| `docker-compose-gen.py` | Docker Compose 生成 | `python scripts/docker-compose-gen.py --type fullstack` |
| `log-analyzer.py` | 日志分析 | `python scripts/log-analyzer.py --file app.log` |
| `heatmap.py` | 代码热力图 | `python scripts/heatmap.py --dir src/` |
| `tech-debt.py` | 技术债务追踪 | `python scripts/tech-debt.py --list` |
| `deploy.py` | 自动化部署 | `python scripts/deploy.py --list` |
| `profiler.py` | 性能分析器 | `python scripts/profiler.py --file main.py` |
| `similarity.py` | 代码相似度检测 | `python scripts/similarity.py --dir src/` |

## 参考库速查

| 文件 | 内容 |
|------|------|
| `references/patterns.md` | 设计模式速查 |
| `references/security.md` | 安全漏洞清单 |
| `references/naming.md` | 多语言命名规范 |
| `references/pr-checklist.md` | PR Review 检查清单 |
| `references/mermaid-templates.md` | 架构图模板 |
| `references/snippets.md` | 常用代码模板 |

## 工作流

```
编写 → 扫描(Bug/安全) → 审查(可读性) → 重构(性能/模式) → 测试(生成) → 文档(生成) → 部署(配置) → 复盘(记录)
```

## 快速开始

```bash
# 运行自测（校验所有脚本可执行）
python scripts/selftest.py

# 常用命令
python scripts/devflow.py --dir . --quick        # 完整流水线（快速模式）
python scripts/review.py --file src/main.py --mode security
```

## 编码问题（Windows）

如遇编码问题，请确保使用 Python 3.10+ 并以 UTF-8 编码运行：`set PYTHONUTF8=1`

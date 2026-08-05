# DevFlow Fullstack

<div align="center">

**一站式全链路开发辅助工具，一条命令接入所有 AI 编程平台。**

覆盖 **编码 → 调试 → 重构 → 部署 → 复盘** 全流程，58 个零依赖 Python 脚本。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Scripts](https://img.shields.io/badge/CLI_Scripts-58-orange)](scripts/)
[![Tests](https://img.shields.io/badge/SelfTest-52%20passed-brightgreen)](scripts/selftest.py)
[![Platforms](https://img.shields.io/badge/AI_Platforms-7-blueviolet)](#-多平台一键接入)
[![Zero Dep](https://img.shields.io/badge/Dependencies-0-red)](pyproject.toml)

</div>

---

## ✨ 项目简介

DevFlow Fullstack 是一个开箱即用的全链路开发辅助工具包：

- **58 个 Python CLI 脚本** — 覆盖代码审查、Bug 扫描、测试生成、文档生成、CI 集成等
- **AST 驱动的代码分析** — `review.py` / `smell.py` / `testgen.py` 用 Python AST 解析，误报率远低于正则
- **零第三方依赖** — 只需 Python 3.10+，`git clone` 即可用
- **多平台一键接入** — Claude Code、Codex、opencode、Cursor、Windsurf、Trae、GitHub Copilot
- **五阶段工作流引擎** — init → plan → code → verify → review，带质量关卡与状态持久化
- **多角色协作** — 8 个专业角色，可串行/并行执行，可选 LLM 汇总
- **可选增强** — 自动调用 Bandit/Ruff/pytest（已安装时），可选接入 LLM 做语义分析
- **CI/CD 开箱即用** — GitHub Actions / GitLab CI 配置文件

---

## 🚀 快速开始

### 方式一：一条命令接入你的项目（推荐）

在你的项目根目录执行：

```bash
# 全部平台接入（Claude Code / Codex / opencode / Cursor / Windsurf / Trae / Copilot）
python setup.py install

# 只接入指定平台
python setup.py install --platform claude,codex,opencode

# 全局安装（Claude 全局命令、Codex skill 到 HOME）
python setup.py install --global --platform codex,claude
```

安装后验证：

```bash
python scripts/selftest.py
```

### 方式二：使用 DevFlow 本体做代码分析

```bash
git clone https://github.com/chenqiyue123/devflow-fullstack.git
cd devflow-fullstack

# 运行自测
python scripts/selftest.py

# 安全扫描
python scripts/review.py --mode security --dir .

# 代码结构分析
python scripts/explain.py --file main.py

# 生成测试
python scripts/testgen.py --file calculator.py --framework pytest
```

### 方式三：pip 安装（统一命令入口）

```bash
pip install .
# 之后可用 devflow 命令
devflow --help
devflow review --mode security --dir .
devflow setup install --platform claude   # 一键接入
```

### 方式四：curl 一键脚本（Linux/macOS）

```bash
curl -fsSL https://raw.githubusercontent.com/chenqiyue123/devflow-fullstack/main/install.sh | bash
```

Windows 用户运行 `install.bat`。

---

## 🔌 多平台一键接入

`python setup.py install` 会自动将 DevFlow 配置复制到你的项目：

| 平台 | 安装内容 | 使用方式 |
|------|---------|---------|
| **Claude Code** | `.claude/commands/` slash 命令 + hooks + `CLAUDE.md` | 打开项目后输入 `/devflow-review` |
| **Codex** | `skills/devflow-fullstack/`（标准 Agent Skill 目录） | 项目级装到 `.agents/skills/`；`--global` 装到 `~/.codex/skills/` |
| **opencode** | `opencode.json` | opencode 打开项目即自动加载 |
| **Cursor** | `.cursorrules` | Cursor 自动加载 |
| **Windsurf** | `.windsurfrules` | Windsurf 自动加载 |
| **Trae** | `.trae/rules` | Trae 自动加载 |
| **GitHub Copilot** | `.github/copilot-instructions.md` | Copilot 自动加载 |

### Claude Code 集成示例

```bash
# 接入 Claude Code
python setup.py install --platform claude

# 在 Claude Code 中使用
/devflow-init      # 初始化五阶段工作流
/devflow-status    # 查看进度
/devflow-review    # 多 Agent 代码审查
/devflow-agents    # 运行指定角色
/devflow-plan      # 生成开发计划
```

保存代码时还会自动触发安全审查 hook（`.claude/settings.json` 配置）。

---

## 📦 核心功能

### 代码审查（AST 驱动）

| 命令 | 说明 |
|------|------|
| `python scripts/review.py --mode security --dir .` | 安全漏洞扫描 |
| `python scripts/review.py --mode all --dir .` | 全量扫描（Bug+安全+可读性） |
| `python scripts/smell.py --dir .` | 代码坏味道检测 |
| `python scripts/review.py --mode deadcode --dir .` | 死代码检测 |
| `python scripts/review.py --mode duplication --dir .` | 重复代码检测 |
| `python scripts/review.py --mode security --dir . --with-tools` | 附加 Bandit/Ruff 结果 |

所有命令支持 `--format json`，便于 CI 集成。

### 代码分析

| 命令 | 说明 |
|------|------|
| `python scripts/explain.py --file main.py` | 结构分析（函数/依赖/复杂度） |
| `python scripts/explain.py --file main.py --line 42` | 解释特定行 |
| `python scripts/explain.py --file main.py --llm` | 语义解释（需配置模型） |

### 测试 / 文档生成

| 命令 | 说明 |
|------|------|
| `python scripts/testgen.py --file calc.py --framework pytest` | 生成测试 |
| `python scripts/testgen.py --file calc.py --llm` | LLM 语义测试 |
| `python scripts/docgen.py --mode all --file main.py` | 生成文档 |

### 工作流 / 多角色

| 命令 | 说明 |
|------|------|
| `python scripts/workflow.py init --dir .` | 初始化五阶段工作流 |
| `python scripts/workflow.py status --dir .` | 查看进度 |
| `python scripts/workflow.py next --dir .` | 运行质量关卡并推进 |
| `python scripts/agents.py --team all --dir .` | 多角色协作 |
| `python scripts/agents.py --team all --dir . --llm` | LLM 汇总各角色结论 |

### 工程化

| 命令 | 说明 |
|------|------|
| `python scripts/config-gen.py --type dockerfile --dir .` | 生成 Dockerfile |
| `python scripts/deps-scan.py --dir .` | 依赖漏洞扫描 |
| `python scripts/git-helper.py --mode commit` | 生成 commit 建议 |
| `python scripts/env-check.py --dir .` | 环境检查 |
| `python scripts/dashboard.py --dir . --format html` | 代码质量仪表盘 |

---

## 🤖 可选增强

### 成熟工具链

安装 Bandit/Ruff 后，`review.py --with-tools` 会自动附加成熟工具的检测结果：

```bash
pip install bandit ruff pytest
python scripts/toolchain.py --check          # 检测工具可用性
python scripts/review.py --mode security --dir . --with-tools
```

### LLM 语义能力

配置模型后，`explain.py` / `testgen.py` / `agents.py` 的 `--llm` 模式提供语义级能力：

```bash
# 配置模型（OpenAI / Claude / 本地 Ollama）
python scripts/model-manager.py --config --provider openai --api-key sk-xxx
# 或设置环境变量 OPENAI_API_KEY / ANTHROPIC_API_KEY

python scripts/llm.py --check                # 检查是否可用
python scripts/explain.py --file main.py --llm
python scripts/testgen.py --file calc.py --llm
python scripts/agents.py --team all --dir . --llm
```

未配置模型时自动回退到启发式，不影响使用。

---

## 🔧 CI/CD 集成

### GitHub Actions

```bash
mkdir -p .github/workflows
cp cicd/github-actions.yml .github/workflows/devflow.yml
git commit -m "ci: add DevFlow code review"
git push
```

自动执行：安全扫描、坏味道检查、依赖扫描、PR 评论、报告产物、高危阻断。

### GitLab CI

```bash
cp cicd/gitlab-ci.yml .gitlab-ci.yml
```

---

## 📁 项目结构

```
devflow-fullstack/
├── scripts/                    # 58 个 Python CLI 脚本（零依赖）
│   ├── review.py               # 代码审查（AST 驱动）
│   ├── smell.py                # 坏味道检测（AST 驱动）
│   ├── testgen.py              # 测试生成（AST 驱动）
│   ├── explain.py              # 代码分析（--llm 语义解释）
│   ├── workflow.py             # 五阶段工作流引擎
│   ├── agents.py               # 多角色协作
│   ├── toolchain.py            # Bandit/Ruff/pytest 桥接
│   ├── llm.py                  # LLM 调用桥接
│   ├── model-manager.py        # 模型配置管理
│   └── ...                     # 更多脚本
├── setup.py                    # 一键安装器（核心）
├── install.sh / install.bat    # 一键安装脚本
├── .claude/                    # Claude Code 集成（命令 + hooks）
├── opencode.json               # opencode 集成
├── .cursorrules                # Cursor 集成
├── .windsurfrules              # Windsurf 集成
├── .trae/rules                 # Trae 集成
├── .github/                    # Copilot 集成 + GitHub Actions
├── skills/devflow-fullstack/     # 标准 Agent Skill（SKILL.md + 脚本）
├── SKILL.md                      # Codex skill 兼容副本
├── agents/openai.yaml            # Codex agent 配置
├── cicd/                       # CI/CD 配置
├── references/                 # 参考库
├── vscode-extension/           # VS Code 插件源码
├── pyproject.toml              # pip 打包配置
├── CLAUDE.md                   # Claude Code 适配说明
├── CHANGELOG.md                # 变更日志
├── CONTRIBUTING.md             # 贡献指南
└── LICENSE                     # MIT 许可证
```

---

## 🛠 开发

```bash
# 运行测试
pip install pytest
python -m pytest tests/ -q

# 运行自测（校验所有脚本可执行）
python scripts/selftest.py
```

### 新增一个脚本

1. 用 `argparse`，参数命名与现有脚本一致
2. 有 docstring，含 Usage 示例
3. 无 BOM
4. 登记到 `scripts/selftest.py`
5. 在 README「核心功能」中记录

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 许可证

MIT License

## 🙏 致谢

感谢每一位使用 DevFlow 的开发者。

如果 DevFlow 帮到了你，点个 ⭐ 就是最好的支持。发现 Bug 或有想法？欢迎提 Issue 和 PR。

愿 DevFlow 陪你写出更干净的代码。

---

**作者**：陈启粤

**日期**：2026-08-05

# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- **一键安装器**：新增 `setup.py` + `install.sh` + `install.bat`
  - `python setup.py install` 一条命令接入 Claude Code / Codex / opencode / Cursor / Windsurf / Trae / Copilot
  - `--platform claude,codex` 指定平台；`--global` 全局安装（claude 全局命令、codex skill）
  - `devflow setup install` 提供 pip 安装后的统一入口
- **opencode 适配**：新增 `opencode.json`
- **CI 可运行化**：`review.py` / `smell.py` / `deps-scan.py` 的 `--format json` 输出纯净合法，CI 配置与真实命令对齐
- 新增 `CONTRIBUTING.md`、`CHANGELOG.md`

### 修复
- VS Code 插件：自动审查不再调用不存在的 `review.py --mode quick`，改为 `--mode security`
- VS Code 插件：`runScript` 改用 `execFile` + 参数数组，修复路径含空格时的调用失败
- VS Code 插件：脚本路径找不到时给出明确报错，不再静默失败
- `SKILL.md`：修复文末乱码段落；重写为命令可验证的可靠版本
- `coverage-scan.py`：低覆盖率退出码从 2 改为 1（符合项目退出码规范）
- 移除含本机路径的 `DEVFLOW_REPORT.md`；移除过时的 `.vsix`（需从源码重建）
- 平台适配文件（.cursorrules/.windsurfrules/.trae/copilot/agents）更新为 58 个脚本的准确描述

### 变更
- **文档诚实性**：README / CLAUDE.md 修正与实际不符的描述
  - 多 Agent 角色数从「9 个」修正为实际的「8 个」
  - 「代码续写 / 多语言互转 / 代码↔口语互译」明确标注为 LLM 增强能力，非 CLI 内置
  - `explain.py` 标注为「结构分析」，非「语义解释」
  - 新增「已知限制」章节
- **AST 化核心扫描**：`review.py` / `smell.py` / `testgen.py` 的 Python 分析改用 AST
  - `review.py`：真实安全/逻辑/性能/复杂度检测
  - `smell.py`：真实函数长度、控制流嵌套、魔法数字、裸 except 等
  - `testgen.py`：基于签名的参数类型推断，方法通过类实例调用，测试可真实运行
  - 非 Python 语言保持正则回退
- **工具链桥接**：新增 `toolchain.py`，自动调用 Bandit/Ruff/pytest
- **LLM 桥接**：新增 `llm.py`，支持 OpenAI/Claude/Azure/本地 Ollama
- **打包**：新增 `pyproject.toml` + `devflow_cli.py`，支持 `pip install .`
- 脚本总数从 56 增至 58

## [1.0.0] - 2026-05-28

首个发布版本。包含 56 个 Python CLI 脚本、VS Code 插件、五阶段工作流引擎、多角色协作层与多平台适配。

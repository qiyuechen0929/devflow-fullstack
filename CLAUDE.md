# DevFlow Fullstack - Claude Code 适配

## 项目简介

一站式全链路开发辅助工具，覆盖 **编码 → 调试 → 重构 → 部署 → 复盘**。

## 核心功能

### 编码辅助
- 语法转换（Python2↔3, ES5↔ES6+，见 `scripts/migrate.py`）
- 正则生成与解释（见 `scripts/regex.py`）
- API 对接辅助（见 `scripts/apitools.py`）
- 代码续写 / 多语言互转（C↔Java, Python↔Go）/ 代码↔口语互译 —— 属 LLM 增强能力，需配合 AI 助手或 `model-manager.py` 配置模型后使用，CLI 脚本本身不内置此能力

### 调试排错
- 多层级 Bug 扫描（L1语法/L2逻辑/L3性能/L4安全）
- 报错日志解析（见 `scripts/log-analyzer.py`）
- 边界用例推演（见 `scripts/boundary.py`）
- 竞态条件分析（见 `scripts/racecheck.py`）

### 重构优化
- 分层重构（格式化→提取函数→OOP改造→设计模式）
- 性能优化
- 冗余清理
- 数据库查询优化

### 工程化
- 文档生成（注释/函数文档/API文档）
- 测试生成（JUnit/Pytest/Jest）
- 配置生成（Dockerfile/CI/CD）
- Commit 生成

### 特色功能
- 代码↔口语互译 / 面试模拟 —— LLM 增强能力，需配置模型后使用
- 学习复盘 / Bug 知识库 —— 通过 `scripts/memory.py` + 记忆目录实现

## 使用命令

```bash
# 全流程运行
python scripts/devflow.py --dir .

# Bug 扫描
python scripts/review.py --mode all --dir .
python scripts/review.py --mode security --file src/main.py

# 代码解释
python scripts/explain.py --file main.py
python scripts/explain.py --file main.py --line 42

# 文档生成
python scripts/docgen.py --mode all --file foo.py

# 测试生成
python scripts/testgen.py --file calculator.py --framework pytest

# 代码坏味道检测
python scripts/smell.py --dir .

# 环境检查
python scripts/env-check.py --dir .

# Git 辅助
python scripts/git-helper.py --mode commit

# 清理调试标记
python scripts/clean-debug.py --dir src/
```

## 工作原则

1. **优先使用脚本** — 本项目的脚本已覆盖常见开发场景
2. **任务反思** — 每次任务结束评分（1-5分），记录经验
3. **说人话** — 给建议时用通俗语言，不堆术语
4. **渐进式** — 复杂任务分步执行，每步可验证

## 参考库

- `references/patterns.md` — 设计模式速查
- `references/security.md` — 安全漏洞清单
- `references/naming.md` — 多语言命名规范
- `references/pr-checklist.md` — PR Review 检查清单
- `references/mermaid-templates.md` — 架构图模板
- `references/snippets.md` — 常用代码模板

## 脚本能力边界（重要）

以下能力**不是** CLI 脚本内置的，需配合 LLM（如 Claude Code / Codex / model-manager 配置的模型）才能实现：

- 代码续写 / 生成
- 多语言语义互转（C↔Java、Python↔Go 等，脚本仅做规则化/结构转换）
- 代码↔口语互译
- 面试模拟
- 智能命名推荐

CLI 脚本提供的是**结构化分析**（AST/正则扫描、统计、模板生成），语义理解部分交给 AI 助手完成。

## 触发场景

当用户提出以下需求时，使用 DevFlow：
1. 代码编写/续写/转换
2. Bug 调试/日志分析
3. 重构/性能优化
4. 文档/测试/配置生成
5. 算法辅助/技术选型

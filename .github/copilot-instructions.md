# DevFlow Fullstack - GitHub Copilot Instructions

## 项目说明

DevFlow 是一站式全链路开发辅助工具，使用 **58 个 Python 脚本**（零第三方依赖），覆盖编码→调试→重构→工程化→CI→LLM 增强。

## 可用工具

当需要进行代码审查、测试生成、文档生成等操作时，使用以下脚本：

### 代码审查与分析（AST 驱动）
- `scripts/review.py` — 多层级 Bug/安全扫描（AST + 正则）
- `scripts/smell.py` — 代码坏味道检测
- `scripts/boundary.py` — 边界用例推演
- `scripts/racecheck.py` — 竞态条件分析
- `scripts/complexity.py` — 代码复杂度分析
- `scripts/todo-scan.py` — TODO/FIXME 扫描

### 代码生成与转换
- `scripts/explain.py` — 代码结构分析（`--llm` 语义解释）
- `scripts/migrate.py` — 语法/语言规则转换
- `scripts/testgen.py` — 测试生成（`--llm` 语义测试）
- `scripts/docgen.py` — 文档生成

### 工程化工具
- `scripts/config-gen.py` — 配置生成（Dockerfile/CI）
- `scripts/git-helper.py` — Git 辅助（Commit/PR/Changelog）
- `scripts/env-check.py` — 环境检查
- `scripts/clean-debug.py` — 清理调试标记
- `scripts/deps-scan.py` — 依赖漏洞扫描

### 工作流 / 多角色 / 增强
- `scripts/workflow.py` — 五阶段工作流引擎
- `scripts/agents.py` — 多角色协作（`--llm` 汇总结论）
- `scripts/toolchain.py` — Bandit/Ruff/pytest 桥接
- `scripts/llm.py` — LLM 调用桥接

## 使用示例

```bash
# 扫描项目中的安全问题
python scripts/review.py --mode security --dir .

# 为指定文件生成测试
python scripts/testgen.py --file src/calculator.py --framework pytest

# 生成代码文档
python scripts/docgen.py --mode all --file src/main.py

# 检查代码质量
python scripts/smell.py --dir src/
```

## 编码规范

1. 使用 Python 3.10+ 特性
2. 保持 UTF-8 编码
3. 函数必须有 docstring
4. 错误处理要完善
5. 优先使用项目脚本完成任务

## 触发条件

当用户的代码涉及以下场景时，建议使用 DevFlow 工具：
- 需要代码审查或安全检查
- 需要生成测试用例
- 需要生成文档
- 需要代码转换或重构
- 需要分析代码质量

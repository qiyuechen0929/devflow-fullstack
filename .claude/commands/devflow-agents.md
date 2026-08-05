---
description: 运行 DevFlow 多 Agent 协作
---

# DevFlow 多 Agent 协作

运行 DevFlow 的专业角色团队。可用角色：

| 角色 | 职责 | 对应脚本 |
|------|------|---------|
| `pm` | 项目管理、commit 建议、git 统计 | git-helper, git-stats |
| `architect` | 架构分析、依赖图、边界推演 | arch-gen, boundary |
| `developer` | 测试生成、文档生成、代码解释 | testgen, docgen, explain |
| `qa` | Bug 扫描、坏味道、竞态分析 | review, smell, racecheck |
| `reviewer` | 安全审查、复杂度、TODO 扫描 | review, complexity, todo-scan |

## 执行步骤

1. 查看所有角色：
```bash
python scripts/agents.py --list
```

2. 运行指定角色（用逗号分隔）：
```bash
python scripts/agents.py --team qa,reviewer --dir .
```

3. 并行运行：
```bash
python scripts/agents.py --team all --dir . --parallel
```

4. 指定要分析的代码文件：
```bash
python scripts/agents.py --team developer --dir . --file src/main.py
```

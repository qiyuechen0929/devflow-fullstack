---
description: 用 DevFlow 多 Agent 团队审查代码
---

# DevFlow 多 Agent 代码审查

使用 DevFlow 的多 Agent 协作层对当前项目进行全面代码审查。

## 执行步骤

1. 运行全部角色审查（pm + architect + developer + qa + reviewer）：
```bash
python scripts/agents.py --team all --dir .
```

2. 或只运行核心审查角色：
```bash
python scripts/agents.py --team qa,reviewer --dir .
```

3. 如需输出 JSON 报告：
```bash
python scripts/agents.py --team all --dir . --format json
```

4. 向用户汇总报告：
   - 各角色的通过率
   - 发现的关键问题（安全、复杂度、TODO 遗留）
   - 修复建议

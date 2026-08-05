---
description: 查看 DevFlow 工作流状态
---

# DevFlow 工作流状态

查看当前项目在 DevFlow 五阶段工作流中的进度。

## 执行步骤

1. 查看状态：
```bash
python scripts/workflow.py status --dir .
```

2. 向用户简洁汇报：
   - 当前阶段
   - 各阶段完成情况（✅ 已完成 / 🔄 进行中 / ⬜ 未开始）
   - 当前阶段的质量关卡要求
   - 建议的下一步操作

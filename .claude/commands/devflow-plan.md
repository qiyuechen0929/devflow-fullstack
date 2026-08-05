---
description: 生成 DevFlow 开发计划
---

# DevFlow 开发计划

为当前项目生成开发计划文档（plan.md），并推进工作流到编码阶段。

## 执行步骤

1. 生成计划文档：
```bash
python scripts/workflow.py plan --dir .
```

2. 查看生成的计划：
```bash
cat plan.md
```

3. 请用户完善计划内容（目标、任务、技术方案），然后运行质量关卡：
```bash
python scripts/workflow.py next --dir .
```

## 注意事项

- plan.md 是后续编码阶段的依据，务必让用户确认内容
- plan 关卡要求 plan.md 包含"目标"和"任务"章节

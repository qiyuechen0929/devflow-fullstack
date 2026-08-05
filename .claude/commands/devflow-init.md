---
description: 初始化 DevFlow 阶段化工作流
---

# DevFlow 工作流初始化

在当前项目上初始化 DevFlow 的五阶段工作流（init → plan → code → verify → review）。

## 执行步骤

1. 运行初始化命令：
```bash
python scripts/workflow.py init --dir .
```

2. 查看初始状态：
```bash
python scripts/workflow.py status --dir .
```

3. 运行 init 阶段质量关卡并进入下一阶段：
```bash
python scripts/workflow.py next --dir .
```

4. 向用户报告：
   - 检测到的项目类型
   - 当前所处阶段
   - 下一阶段该做什么

## 注意事项

- 如果项目已有 `.devflow/state.json`，说明已初始化过，直接运行 `status` 查看进度
- init 关卡要求能识别项目类型，否则会停留在 init 阶段

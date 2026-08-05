# 贡献指南

感谢你对 DevFlow Fullstack 感兴趣！本文件说明如何参与贡献。

## 项目定位

DevFlow Fullstack 是**零依赖、标准库优先**的全链路开发辅助工具。新增功能时请遵循这一原则：
优先使用 Python 标准库实现；需要第三方依赖才能实现的功能，请放在 `[project.optional-dependencies]` 中，并保证主 CLI 在无依赖时仍可运行。

## 开发环境

```bash
# 开发模式运行
python devflow_cli.py <command>

# 运行测试（需 pytest）
pip install -e .[dev]
pytest

# 运行自测（校验所有脚本可执行）
python scripts/selftest.py
```

## 代码规范

1. **Python 3.10+**，只使用标准库（除非是可选增强）
2. 所有脚本支持 `--dir` / `--file` 定位目标，输出保持文本 + 可选 `--format json`
3. 退出码约定：
   - `0` — 正常执行
   - `1` — 执行成功但发现问题（安全漏洞、坏味道等）
   - `2` — 参数错误 / 目标不存在
4. 新增脚本后，必须在 `scripts/selftest.py` 的脚本清单中登记
5. 文档（README / CLAUDE.md / SKILL.md）与实现保持同步——**禁止宣称不存在的功能**

## 提交规范

```bash
python scripts/git-helper.py --mode commit
```

遵循 Conventional Commits：`feat:` `fix:` `docs:` `refactor:` `chore:`。

## 新增一个脚本的检查清单

- [ ] 用 `argparse`，参数命名与现有脚本一致
- [ ] 有 docstring，含 Usage 示例
- [ ] 无 BOM（`file` 应显示 UTF-8 无 BOM）
- [ ] 已登记到 `selftest.py`
- [ ] 已在 README「功能一览」中记录（若为对外功能）
- [ ] 有测试（`tests/` 下，若逻辑可测）

## 报告问题

请到 GitHub Issues 提交，包含：
- 复现步骤 / 最小示例
- 预期行为与实际行为
- 你的 Python 版本与操作系统

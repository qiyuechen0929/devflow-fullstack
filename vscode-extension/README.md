# DevFlow Fullstack - VS Code Extension

一站式全链路开发辅助工具，覆盖 **编码 → 调试 → 重构 → 部署 → 复盘**。

## 功能

| 命令 | 说明 | 快捷键 |
|------|------|--------|
| `DevFlow: Code Review` | 多层级代码审查（Bug/可读性/死代码） | `Ctrl+Shift+R` |
| `DevFlow: Security Scan` | 安全漏洞扫描 | `Ctrl+Shift+S` |
| `DevFlow: Explain Code` | 代码解释（代码→人话） | `Ctrl+Shift+E` |
| `DevFlow: Generate Tests` | 生成测试用例（pytest） | - |
| `DevFlow: Generate Documentation` | 生成代码文档 | - |
| `DevFlow: Format Code` | 代码格式化检查 | - |
| `DevFlow: Check Dependencies` | 依赖漏洞扫描 | - |
| `DevFlow: Generate Changelog` | 生成变更日志 | - |
| `DevFlow: Show Dashboard` | 代码质量仪表盘 | - |
| `DevFlow: Generate Docker Compose` | 生成 Docker Compose | - |

## 特性

- **右键菜单集成**：在编辑器或资源管理器中右键即可调用审查/解释/测试功能
- **自动审查**：开启后保存文件时自动进行安全扫描（可在设置中关闭）
- **Webview 输出**：代码解释和仪表盘以富文本面板展示
- **可配置 Python 路径**：支持自定义 Python 解释器

## 安装

### 从 VSIX 安装

1. 下载 `devflow-fullstack-1.0.0.vsix`
2. 在 VS Code 中按 `Ctrl+Shift+P`
3. 输入 `Extensions: Install from VSIX...`
4. 选择下载的 `.vsix` 文件

### 从源码构建

```bash
cd vscode-extension
npm install
npm run compile
npm run package
```

> 注意：扩展运行依赖 DevFlow 脚本（`scripts/` 目录）。
> 首次使用时，在 VS Code 设置中配置 `devflow.scriptsPath`，指向 DevFlow 仓库的 `scripts/` 目录；
> 或在 DevFlow 项目根目录运行 `python setup.py install --platform vscode` 前先确认脚本位置。

## 配置

在 VS Code 设置中搜索 `devflow`：

```json
{
  "devflow.pythonPath": "python",
  "devflow.scriptsPath": "/path/to/devflow-fullstack/scripts",
  "devflow.outputFormat": "text",
  "devflow.autoReview": false
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `devflow.pythonPath` | Python 解释器路径 | `python` |
| `devflow.scriptsPath` | DevFlow 脚本路径（必须指向含 `review.py` 的目录） | `""` |
| `devflow.outputFormat` | 输出格式 | `text` |
| `devflow.autoReview` | 保存时自动审查 | `false` |

## 要求

- VS Code 1.80.0+
- Python 3.10+
- DevFlow 脚本（通过 `devflow.scriptsPath` 配置，或使用 `setup.py` 安装到项目）

## 许可证

MIT

# DevFlow CI/CD Integration

DevFlow 提供开箱即用的 CI 配置，零第三方依赖（只需 Python 3.10+）。

## GitHub Actions

### 快速开始

```bash
# 在项目根目录
mkdir -p .github/workflows
cp cicd/github-actions.yml .github/workflows/devflow.yml

git add .github/workflows/devflow.yml
git commit -m "ci: add DevFlow code review"
git push
```

### 功能

- ✅ 自测（selftest）确保脚本可用
- ✅ 安全漏洞扫描（review.py --mode security）
- ✅ 代码坏味道检查（smell.py）
- ✅ 依赖漏洞检测（deps-scan.py）
- ✅ PR 自动评论（含高危安全问题摘要）
- ✅ 生成报告产物（artifact）
- ✅ 高危安全问题阻断合并

### 可选增强

CI 默认使用自研零依赖脚本。如需接入成熟工具（Bandit/Ruff），在 workflow 中加一行：

```yaml
- name: Install optional tools
  run: pip install bandit ruff
```

之后 `review.py --with-tools` 会自动附加 Bandit/Ruff 结果。

---

## GitLab CI

### 快速开始

```bash
cp cicd/gitlab-ci.yml .gitlab-ci.yml

git add .gitlab-ci.yml
git commit -m "ci: add DevFlow code review"
git push
```

### 功能

- ✅ 安全漏洞扫描
- ✅ 代码质量检查（坏味道 + 依赖）
- ✅ 自测
- ✅ MR 报告生成

---

## 本地使用

```bash
# 安全扫描（JSON 输出供 CI/脚本消费）
python scripts/review.py --mode security --dir . --format json

# 代码质量
python scripts/smell.py --dir . --format json

# 依赖扫描
python scripts/deps-scan.py --dir . --format json

# PR 审查
git diff main...feature > pr.diff
python scripts/pr-review.py --file pr.diff --format json
```

## 输出格式

所有 CI 相关脚本均支持 `--format json`，输出为合法的 JSON：

```json
// review.py / smell.py
{ "total": 3, "issues": [ ... ] }

// deps-scan.py
{ "total": 0, "vulnerabilities": [], "dependencies": [] }
```

---

## 常见问题

### Q: 如何只扫描特定目录？

```bash
python scripts/review.py --mode security --dir src/
```

### Q: 如何忽略某些文件？

创建 `.devflowignore` 文件（或修改脚本内 ignore 集合）：
```
node_modules/
vendor/
*.min.js
```

### Q: 如何调整失败阈值？

编辑 CI 中 `Fail on Critical Issues` 步骤的判断条件，例如只在高危数量 > 0 时失败：

```yaml
if: steps.security.outputs.total > 0
```

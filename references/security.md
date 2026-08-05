# Security Vulnerability Checklist

## Web 常见漏洞

| 漏洞 | 表现 | 修复 |
|------|------|------|
| **SQL 注入** | 字符串拼接 SQL | 参数化查询 / ORM |
| **XSS** | innerHTML/eval 用户输入 | 转义输出 / DOMPurify / CSP |
| **CSRF** | 跨站请求伪造 | CSRF Token / SameSite Cookie |
| **SSRF** | 服务端请求伪造 | URL 白名单 / 禁止内网请求 |
| **路径遍历** | `../../etc/passwd` | 路径规范化 / 白名单 |
| **IDOR** | 越权访问他人数据 | 每次请求校验所有权 |

## 代码层常见漏洞

| 漏洞类型 | 触发条件 | 危险等级 |
|---------|---------|:---:|
| 硬编码密钥 | 代码中含 API Key/密码 | 🔴 严重 |
| 弱加密算法 | MD5/SHA1/DES/RC4 | 🔴 严重 |
| 命令注入 | os.system() 拼接用户输入 | 🔴 严重 |
| 反序列化攻击 | pickle/yaml.load 不可信数据 | 🔴 严重 |
| 竞态条件 | 多线程操作共享变量无锁 | 🟠 高危 |
| 资源泄漏 | 文件句柄/连接未关闭 | 🟡 中危 |
| 空指针 | 未判空直接调用方法 | 🟡 中危 |
| 整数溢出 | 大数运算未做保护 | 🟡 中危 |

## 扫描命令

```bash
# 用 DevFlow review 脚本扫描
python scripts/review.py --mode security --dir src/

# 或直接让 Skills 检查：
# "帮我扫描 xx.java 的安全漏洞"
```

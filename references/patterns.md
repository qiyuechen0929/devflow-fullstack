# Design Patterns Quick Reference

## 创建型 (Creational)

| 模式 | 场景 | 一句话 |
|------|------|--------|
| **Singleton** | 全局唯一（日志器/配置/连接池） | 整个应用只用一个实例 |
| **Factory Method** | 根据参数创建不同类型对象 | 把 new 外包给工厂 |
| **Builder** | 多步骤构建复杂对象 | 链式 .build() 替代臃肿构造函数 |
| **Prototype** | 克隆对象而非新建 | 省去重新初始化的开销 |

## 结构型 (Structural)

| 模式 | 场景 | 一句话 |
|------|------|--------|
| **Adapter** | 老接口适配新系统 | 三孔插座转两孔 |
| **Decorator** | 动态增强功能 | Python @decorator, React HOC |
| **Facade** | 简化复杂子系统 | 一键启动 vs 逐个开关 |
| **Proxy** | 控制访问（缓存/权限/延迟加载） | 代理帮真实对象挡刀 |

## 行为型 (Behavioral)

| 模式 | 场景 | 一句话 |
|------|------|--------|
| **Observer** | 一对多通知（事件/消息） | 订阅-发布 |
| **Strategy** | 算法可互换 | 支付方式切换 |
| **Chain of Responsibility** | 多级审批/中间件 | Express/Koa 中间件 |
| **Command** | 撤销/重做/队列 | Ctrl+Z 的原理 |

## 推荐规则

- 看到 `if/switch` 判断类型 → 考虑 **Strategy** 或 **Factory**
- 看到多层嵌套调用 → 考虑 **Facade**
- 看到多个组件需要同步状态 → 考虑 **Observer**
- 看到大量参数构造对象 → 考虑 **Builder**

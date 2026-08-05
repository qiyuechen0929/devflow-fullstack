# Naming Conventions

## 通用原则
- 名字即文档：看名字就知道干什么
- 长度与作用域成正比：全局变量要详细，循环变量可简短
- 布尔值用 is/has/can/should 开头
- 避免缩写，除非是公认的（id, url, api, db）

## Java
- 类: PascalCase → `UserService`, `OrderController`
- 方法: camelCase → `getUserById()`, `calculateTotal()`
- 常量: UPPER_SNAKE → `MAX_RETRY_COUNT`
- 包名: 小写点分 → `com.example.user.service`

## Python
- 类: PascalCase → `UserService`
- 函数/变量: snake_case → `get_user_by_id`, `total_amount`
- 常量: UPPER_SNAKE → `MAX_RETRY_COUNT`
- 私有: `_` 前缀 → `_internal_helper()`

## TypeScript / React
- 组件: PascalCase → `UserProfile`, `ExpenseCard`
- Hook: use前缀 + camelCase → `useUserData`, `useDebounce`
- 事件处理: handle前缀 → `handleSubmit`, `handleClick`
- 类型/接口: PascalCase → `UserProps`, `ExpenseType`
- Props: 组件名 + Props → `ButtonProps`

## Go
- 导出: PascalCase → `GetUser`
- 私有: camelCase → `getUser`
- 缩写全大写: `HTTPServer` 不是 `HttpServer`

## 反例
| 不好 | 好 |
|------|-----|
| `d` | `elapsedDays` |
| `processData()` | `calculateMonthlyAverage()` |
| `flag` | `isValid` / `hasPermission` |
| `tmp` | `tempFilePath` |
| `val` | `discountedPrice` |

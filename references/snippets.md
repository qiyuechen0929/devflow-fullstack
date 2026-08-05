# Code Snippets Templates

## React + TypeScript

### 受控表单组件
```tsx
const [value, setValue] = useState("")
return <input value={value} onChange={e => setValue(e.target.value)} />
```

### API Hook
```tsx
function useApi<T>(url: string) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  
  useEffect(() => {
    fetch(url).then(r => r.json()).then(setData).catch(setError).finally(() => setLoading(false))
  }, [url])
  
  return { data, loading, error }
}
```

### 自定义 Hook (带防抖)
```tsx
function useDebounce<T>(value: T, delay = 300) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}
```

## Python

### 带重试的 HTTP 请求
```python
import requests, time

def fetch_with_retry(url, retries=3, backoff=2):
    for i in range(retries):
        try:
            return requests.get(url, timeout=10)
        except requests.RequestException:
            if i == retries - 1: raise
            time.sleep(backoff ** i)
```

### 单例模式
```python
class Singleton:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

## Java

### Builder 模式
```java
public class User {
    private final String name;
    private final int age;
    
    private User(Builder b) { this.name = b.name; this.age = b.age; }
    
    public static class Builder {
        private String name; private int age;
        public Builder name(String n) { name = n; return this; }
        public Builder age(int a) { age = a; return this; }
        public User build() { return new User(this); }
    }
}
```

## Go

### HTTP 服务最小模板
```go
func main() {
    http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.Write([]byte("OK"))
    })
    http.ListenAndServe(":8080", nil)
}
```

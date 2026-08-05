#!/usr/bin/env python3
"""
DevFlow - LLM 桥接层

统一封装 LLM 调用，供 explain / testgen / agents 等脚本的可选 --llm 模式使用。
复用 model-manager.py 的配置（~/.devflow/models.json + 环境变量）。

设计原则：
- 零第三方依赖：使用标准库 urllib 调用 OpenAI 兼容 /chat/completions 端点
- 若已安装 openai/anthropic SDK 则优先使用（可选增强）
- 未配置 API key 时 is_available() 返回 False，调用方自动回退到启发式

Usage:
  from llm import is_available, chat, get_active_provider
"""

import json
import os
import urllib.request
from pathlib import Path

CONFIG_DIR = Path.home() / ".devflow"
CONFIG_FILE = CONFIG_DIR / "models.json"

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-haiku-20240307",
    },
    "local": {
        "name": "Local Model (Ollama)",
        "env_key": None,
        "base_url": "http://localhost:11434",
        "model": "llama3",
    },
    "azure": {
        "name": "Azure OpenAI",
        "env_key": "AZURE_API_KEY",
        "base_url": "",
        "model": "gpt-4o-mini",
    },
}


def _load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"default_provider": "openai", "providers": {}}


def get_active_provider():
    """返回当前激活的 provider id"""
    cfg = _load_config()
    return cfg.get("default_provider", "openai")


def get_api_key(provider=None):
    """获取 API key：优先环境变量，其次配置文件"""
    provider = provider or get_active_provider()
    env_key = PROVIDERS.get(provider, {}).get("env_key")
    if env_key:
        key = os.environ.get(env_key)
        if key:
            return key
    cfg = _load_config()
    return cfg.get("providers", {}).get(provider, {}).get("api_key")


def get_model(provider=None):
    """获取模型名：优先配置文件，其次默认"""
    provider = provider or get_active_provider()
    cfg = _load_config()
    configured = cfg.get("providers", {}).get(provider, {}).get("default_model")
    if configured:
        return configured
    return PROVIDERS.get(provider, {}).get("model")


def get_base_url(provider=None):
    """获取 base_url：优先配置文件，其次默认"""
    provider = provider or get_active_provider()
    cfg = _load_config()
    configured = cfg.get("providers", {}).get(provider, {}).get("base_url")
    if configured:
        return configured.rstrip("/")
    return PROVIDERS.get(provider, {}).get("base_url", "").rstrip("/")


def is_available(provider=None):
    """LLM 是否可用：local 检查端口，其余检查 API key"""
    provider = provider or get_active_provider()
    if provider == "local":
        return True  # 假设本地服务可能运行；实际调用失败会抛异常
    return bool(get_api_key(provider))


def _chat_openai_compatible(base_url, api_key, model, messages, max_tokens):
    """调用 OpenAI 兼容 /chat/completions 端点"""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _chat_ollama(base_url, model, messages, max_tokens):
    """调用本地 Ollama /api/chat 端点"""
    url = base_url.rstrip("/") + "/api/chat"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["message"]["content"]


def _chat_anthropic(base_url, api_key, model, messages, max_tokens):
    """调用 Anthropic Messages API"""
    url = base_url.rstrip("/") + "/messages"
    # 转换 OpenAI 消息格式 → Anthropic 格式
    system_msgs = [m["content"] for m in messages if m["role"] == "system"]
    convo = [m for m in messages if m["role"] != "system"]
    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": "\n".join(system_msgs) if system_msgs else None,
        "messages": convo,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", "2023-06-01")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(block.get("text", "") for block in data.get("content", []))


def chat(prompt, system=None, provider=None, max_tokens=2048):
    """发送对话，返回 LLM 文本响应。

    参数:
        prompt: 用户消息
        system: 可选的 system 提示
        provider: 显式指定 provider（默认用配置的）
        max_tokens: 最大输出 token
    返回:
        str 响应文本
    异常:
        RuntimeError / urllib 错误
    """
    provider = provider or get_active_provider()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    api_key = get_api_key(provider)
    model = get_model(provider)
    base_url = get_base_url(provider)

    if provider == "local":
        return _chat_ollama(base_url, model, messages, max_tokens)
    if provider == "claude":
        if not api_key:
            raise RuntimeError(f"未配置 {PROVIDERS['claude']['name']} API key")
        return _chat_anthropic(base_url, api_key, model, messages, max_tokens)
    # openai / azure / 其他 OpenAI 兼容端点
    if not api_key:
        raise RuntimeError(f"未配置 {PROVIDERS.get(provider, {}).get('name', provider)} API key")
    return _chat_openai_compatible(base_url, api_key, model, messages, max_tokens)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DevFlow LLM 桥接层")
    parser.add_argument("--check", action="store_true", help="检查 LLM 是否可用")
    parser.add_argument("--provider", help="指定 provider")
    parser.add_argument("--prompt", help="发送一条提示")
    args = parser.parse_args()

    if args.check:
        prov = args.provider or get_active_provider()
        print(f"provider: {prov}")
        print(f"model: {get_model(prov)}")
        print(f"base_url: {get_base_url(prov)}")
        print(f"available: {'✅' if is_available(prov) else '❌'}")
    elif args.prompt:
        try:
            print(chat(args.prompt, provider=args.provider))
        except Exception as e:
            print(f"LLM 调用失败: {e}", file=__import__("sys").stderr)
    else:
        parser.print_help()

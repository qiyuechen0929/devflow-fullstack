#!/usr/bin/env python3
"""
DevFlow - Model Manager
支持 OpenAI/Claude/本地模型切换
Usage:
  python model-manager.py --list
  python model-manager.py --set-default openai
  python model-manager.py --test --model openai
  python model-manager.py --config --api-key sk-xxx --provider openai
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 配置文件路径
CONFIG_DIR = Path.home() / ".devflow"
CONFIG_FILE = CONFIG_DIR / "models.json"

# 支持的模型提供商
PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com"
    },
    "local": {
        "name": "Local Model",
        "models": ["llama", "mistral", "codellama"],
        "env_key": None,
        "base_url": "http://localhost:11434"
    },
    "azure": {
        "name": "Azure OpenAI",
        "models": ["gpt-4", "gpt-35-turbo"],
        "env_key": "AZURE_API_KEY",
        "base_url": "https://{resource}.openai.azure.com"
    }
}


def ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict:
    """加载配置"""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "default_provider": "openai",
        "providers": {},
        "created_at": "",
        "updated_at": ""
    }


def save_config(config: Dict):
    """保存配置"""
    ensure_config_dir()
    from datetime import datetime
    config["updated_at"] = datetime.now().isoformat()
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def configure_provider(provider: str, api_key: str = None, base_url: str = None, model: str = None):
    """配置模型提供商"""
    if provider not in PROVIDERS:
        print(f"Error: Unknown provider '{provider}'", file=sys.stderr)
        print(f"Supported providers: {', '.join(PROVIDERS.keys())}", file=sys.stderr)
        return False

    config = load_config()

    if provider not in config["providers"]:
        config["providers"][provider] = {}

    if api_key:
        config["providers"][provider]["api_key"] = api_key

    if base_url:
        config["providers"][provider]["base_url"] = base_url

    if model:
        config["providers"][provider]["default_model"] = model

    save_config(config)
    return True


def set_default_provider(provider: str):
    """设置默认提供商"""
    if provider not in PROVIDERS:
        print(f"Error: Unknown provider '{provider}'", file=sys.stderr)
        return False

    config = load_config()
    config["default_provider"] = provider
    save_config(config)
    return True


def get_api_key(provider: str) -> Optional[str]:
    """获取 API Key"""
    # 先从环境变量获取
    env_key = PROVIDERS.get(provider, {}).get("env_key")
    if env_key:
        key = os.environ.get(env_key)
        if key:
            return key

    # 再从配置文件获取
    config = load_config()
    return config.get("providers", {}).get(provider, {}).get("api_key")


def test_provider(provider: str) -> bool:
    """测试提供商连接"""
    api_key = get_api_key(provider)

    if not api_key and provider != "local":
        print(f"Error: No API key configured for {provider}", file=sys.stderr)
        print(f"Set via: python model-manager.py --config --provider {provider} --api-key YOUR_KEY", file=sys.stderr)
        return False

    print(f"Testing {PROVIDERS[provider]['name']}...")

    if provider == "openai":
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say 'OK'"}],
                max_tokens=10
            )
            print(f"Success: {response.choices[0].message.content}")
            return True
        except ImportError:
            print("Error: openai package not installed. Run: pip install openai")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False

    elif provider == "claude":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Say 'OK'"}]
            )
            print(f"Success: {response.content[0].text}")
            return True
        except ImportError:
            print("Error: anthropic package not installed. Run: pip install anthropic")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False

    elif provider == "local":
        import urllib.request
        try:
            response = urllib.request.urlopen("http://localhost:11434/api/tags")
            print("Success: Local model server is running")
            return True
        except Exception as e:
            print(f"Error: Local model server not running. Start with: ollama serve")
            return False

    return False


def list_providers():
    """列出所有提供商"""
    config = load_config()
    default = config.get("default_provider", "openai")

    print("Available Providers:")
    print("=" * 60)

    for provider_id, provider_info in PROVIDERS.items():
        is_default = " [DEFAULT]" if provider_id == default else ""
        has_key = "[OK]" if get_api_key(provider_id) else "[NO]"

        print(f"\n{provider_info['name']}{is_default}")
        print(f"  ID: {provider_id}")
        print(f"  API Key: {has_key}")
        print(f"  Models: {', '.join(provider_info['models'])}")
        print(f"  Base URL: {provider_info['base_url']}")


def show_config():
    """显示当前配置"""
    config = load_config()

    print("Current Configuration:")
    print("=" * 60)
    print(f"Default Provider: {config.get('default_provider', 'N/A')}")
    print()

    for provider_id, provider_config in config.get("providers", {}).items():
        print(f"[{provider_id}]")
        if "api_key" in provider_config:
            masked_key = provider_config["api_key"][:8] + "..." if len(provider_config["api_key"]) > 8 else "***"
            print(f"  API Key: {masked_key}")
        if "base_url" in provider_config:
            print(f"  Base URL: {provider_config['base_url']}")
        if "default_model" in provider_config:
            print(f"  Default Model: {provider_config['default_model']}")
        print()


def generate_code_example(provider: str) -> str:
    """生成代码示例"""
    api_key = get_api_key(provider)

    if provider == "openai":
        return f'''import openai

# Configure
client = openai.OpenAI(api_key="{api_key or 'YOUR_API_KEY'}")

# Generate
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {{"role": "system", "content": "You are a helpful assistant."}},
        {{"role": "user", "content": "Explain this code: print('hello')"}}
    ]
)

print(response.choices[0].message.content)
'''

    elif provider == "claude":
        return f'''import anthropic

# Configure
client = anthropic.Anthropic(api_key="{api_key or 'YOUR_API_KEY'}")

# Generate
response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1024,
    messages=[
        {{"role": "user", "content": "Explain this code: print('hello')"}}
    ]
)

print(response.content[0].text)
'''

    elif provider == "local":
        return '''import urllib.request
import json

# Configure
url = "http://localhost:11434/api/generate"

# Generate
data = {
    "model": "llama2",
    "prompt": "Explain this code: print('hello')",
    "stream": False
}

response = urllib.request.urlopen(url, json.dumps(data).encode())
result = json.loads(response.read())

print(result["response"])
'''

    return ""


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Model Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List providers
  python model-manager.py --list

  # Configure provider
  python model-manager.py --config --provider openai --api-key sk-xxx

  # Set default provider
  python model-manager.py --set-default claude

  # Test connection
  python model-manager.py --test --provider openai

  # Show config
  python model-manager.py --show

  # Generate code example
  python model-manager.py --example --provider openai
        """
    )

    parser.add_argument("--list", action="store_true", help="List providers")
    parser.add_argument("--config", action="store_true", help="Configure provider")
    parser.add_argument("--set-default", help="Set default provider")
    parser.add_argument("--test", action="store_true", help="Test provider")
    parser.add_argument("--show", action="store_true", help="Show config")
    parser.add_argument("--example", action="store_true", help="Generate code example")
    parser.add_argument("--provider", "-p", help="Provider name")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--base-url", help="Base URL")
    parser.add_argument("--model", "-m", help="Default model")

    args = parser.parse_args()

    # 列出提供商
    if args.list:
        list_providers()
        return

    # 配置提供商
    if args.config:
        if not args.provider:
            print("Error: --provider is required for --config", file=sys.stderr)
            sys.exit(1)

        if configure_provider(args.provider, args.api_key, args.base_url, args.model):
            print(f"Provider '{args.provider}' configured.")
        return

    # 设置默认提供商
    if args.set_default:
        if set_default_provider(args.set_default):
            print(f"Default provider set to: {args.set_default}")
        return

    # 测试提供商
    if args.test:
        provider = args.provider or load_config().get("default_provider", "openai")
        test_provider(provider)
        return

    # 显示配置
    if args.show:
        show_config()
        return

    # 生成代码示例
    if args.example:
        provider = args.provider or load_config().get("default_provider", "openai")
        example = generate_code_example(provider)
        print(f"Code example for {PROVIDERS[provider]['name']}:")
        print("-" * 60)
        print(example)
        return

    # 默认显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()

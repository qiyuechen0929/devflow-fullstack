#!/usr/bin/env python3
"""
DevFlow - Deployment Script
一键部署脚本
Usage:
  python deploy.py --env production --platform vercel
  python deploy.py --env staging --platform docker
  python deploy.py --env production --platform aws
  python deploy.py --check
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 部署平台配置
PLATFORMS = {
    "vercel": {
        "name": "Vercel",
        "commands": {
            "check": "vercel --version",
            "deploy": "vercel --prod",
            "deploy_staging": "vercel"
        },
        "env_file": ".env",
        "config_file": "vercel.json"
    },
    "netlify": {
        "name": "Netlify",
        "commands": {
            "check": "netlify --version",
            "deploy": "netlify deploy --prod",
            "deploy_staging": "netlify deploy"
        },
        "env_file": ".env",
        "config_file": "netlify.toml"
    },
    "docker": {
        "name": "Docker",
        "commands": {
            "check": "docker --version",
            "build": "docker build -t app .",
            "deploy": "docker-compose up -d",
            "stop": "docker-compose down"
        },
        "env_file": ".env",
        "config_file": "docker-compose.yml"
    },
    "aws": {
        "name": "AWS",
        "commands": {
            "check": "aws --version",
            "deploy": "aws s3 sync . s3://my-bucket",
            "eb_deploy": "eb deploy"
        },
        "env_file": ".env",
        "config_file": "aws-config.json"
    },
    "gcp": {
        "name": "Google Cloud",
        "commands": {
            "check": "gcloud --version",
            "deploy": "gcloud app deploy"
        },
        "env_file": ".env",
        "config_file": "app.yaml"
    },
    "heroku": {
        "name": "Heroku",
        "commands": {
            "check": "heroku --version",
            "deploy": "git push heroku main",
            "logs": "heroku logs --tail"
        },
        "env_file": ".env",
        "config_file": "Procfile"
    },
    "fly": {
        "name": "Fly.io",
        "commands": {
            "check": "fly version",
            "deploy": "fly deploy"
        },
        "env_file": ".env",
        "config_file": "fly.toml"
    },
    "railway": {
        "name": "Railway",
        "commands": {
            "check": "railway version",
            "deploy": "railway up"
        },
        "env_file": ".env",
        "config_file": "railway.json"
    }
}


def run_command(cmd: str, cwd: str = ".") -> Tuple[str, int]:
    """运行命令（使用参数列表方式，避免 shell 注入风险）"""
    try:
        # 使用 shlex.split 将命令拆分为参数列表，并以 shell=False 方式执行
        cmd_args = shlex.split(cmd)
        result = subprocess.run(
            cmd_args,
            shell=False,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return result.stdout.strip() + result.stderr.strip(), result.returncode
    except FileNotFoundError:
        return "命令不存在，请确认对应平台 CLI 已安装", -1
    except Exception as e:
        return str(e), -1


def check_platform(platform: str) -> bool:
    """检查平台是否可用"""
    if platform not in PLATFORMS:
        print(f"Error: Unknown platform '{platform}'", file=sys.stderr)
        return False

    config = PLATFORMS[platform]
    check_cmd = config["commands"].get("check")

    if check_cmd:
        output, code = run_command(check_cmd)
        if code == 0:
            print(f"[OK] {config['name']} is available")
            print(f"  {output[:100]}")
            return True
        else:
            print(f"[FAIL] {config['name']} is not available")
            print(f"  {output[:100]}")
            return False

    return True


def check_prerequisites(platform: str, directory: str = ".") -> List[str]:
    """检查部署前提条件"""
    issues = []
    dir_path = Path(directory)

    # 检查配置文件
    if platform in PLATFORMS:
        config_file = PLATFORMS[platform].get("config_file")
        if config_file and not (dir_path / config_file).exists():
            issues.append(f"Missing config file: {config_file}")

    # 检查 .gitignore
    if not (dir_path / ".gitignore").exists():
        issues.append("Missing .gitignore file")

    # 检查 README
    if not (dir_path / "README.md").exists():
        issues.append("Missing README.md")

    # 检查 package.json (Node.js 项目)
    if (dir_path / "package.json").exists():
        if not (dir_path / "node_modules").exists():
            issues.append("node_modules not found - run 'npm install' first")

    # 检查 requirements.txt (Python 项目)
    if (dir_path / "requirements.txt").exists():
        # 检查虚拟环境
        if not (dir_path / "venv").exists() and not (dir_path / ".venv").exists():
            issues.append("Virtual environment not found")

    return issues


def load_env_file(env_file: str) -> Dict[str, str]:
    """加载环境变量文件"""
    env_vars = {}

    try:
        content = Path(env_file).read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip().strip("'\"")
    except Exception:
        pass

    return env_vars


def deploy(platform: str, env: str = "production", directory: str = ".", dry_run: bool = False) -> bool:
    """执行部署"""
    if platform not in PLATFORMS:
        print(f"Error: Unknown platform '{platform}'", file=sys.stderr)
        return False

    config = PLATFORMS[platform]

    # 选择部署命令
    if env == "staging":
        deploy_cmd = config["commands"].get("deploy_staging", config["commands"].get("deploy"))
    else:
        deploy_cmd = config["commands"].get("deploy")

    if not deploy_cmd:
        print(f"Error: No deploy command for {platform}", file=sys.stderr)
        return False

    # 加载环境变量
    env_file = Path(directory) / config.get("env_file", ".env")
    if env_file.exists():
        env_vars = load_env_file(str(env_file))
        os.environ.update(env_vars)
        print(f"Loaded {len(env_vars)} environment variables")

    # 执行部署
    if dry_run:
        print(f"[DRY RUN] Would execute: {deploy_cmd}")
        return True

    print(f"Deploying to {config['name']} ({env})...")
    output, code = run_command(deploy_cmd, directory)

    if code == 0:
        print(f"[OK] Deployment successful!")
        if output:
            print(output[:500])
        return True
    else:
        print(f"[FAIL] Deployment failed!")
        if output:
            print(output[:500])
        return False


def generate_deploy_script(platform: str, env: str = "production") -> str:
    """生成部署脚本"""
    if platform not in PLATFORMS:
        return ""

    config = PLATFORMS[platform]

    script = f"""#!/bin/bash
# DevFlow Deployment Script
# Platform: {config['name']}
# Environment: {env}

set -e

echo "Deploying to {config['name']} ({env})..."

"""

    # 添加前提检查
    script += "# Check prerequisites\n"
    if platform in ("vercel", "netlify", "fly", "railway"):
        script += f"command -v {platform} >/dev/null 2>&1 || {{ echo '{platform} CLI not found'; exit 1; }}\n"
    elif platform == "docker":
        script += "command -v docker >/dev/null 2>&1 || { echo 'Docker not found'; exit 1; }\n"
        script += "command -v docker-compose >/dev/null 2>&1 || { echo 'Docker Compose not found'; exit 1; }\n"

    script += "\n# Load environment\n"
    script += 'if [ -f .env ]; then\n'
    script += '    export $(cat .env | grep -v "^#" | xargs)\n'
    script += 'fi\n'

    script += "\n# Deploy\n"
    if env == "staging":
        script += f"{config['commands'].get('deploy_staging', config['commands'].get('deploy', ''))}\n"
    else:
        script += f"{config['commands'].get('deploy', '')}\n"

    script += '\necho "Deployment complete!"\n'

    return script


def list_platforms():
    """列出可用平台"""
    print("Available Platforms:")
    print("=" * 60)
    for platform_id, config in PLATFORMS.items():
        print(f"  {platform_id}: {config['name']}")
    print("")


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Deployment Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy to Vercel (production)
  python deploy.py --platform vercel --env production

  # Deploy to Docker (staging)
  python deploy.py --platform docker --env staging

  # Check prerequisites
  python deploy.py --check --platform vercel

  # Generate deploy script
  python deploy.py --generate --platform docker --output deploy.sh

  # List platforms
  python deploy.py --list
        """
    )

    parser.add_argument("--platform", "-p", choices=list(PLATFORMS.keys()), help="Deployment platform")
    parser.add_argument("--env", "-e", choices=["production", "staging"], default="production",
                        help="Deployment environment")
    parser.add_argument("--dir", "-d", default=".", help="Project directory")
    parser.add_argument("--check", action="store_true", help="Check prerequisites")
    parser.add_argument("--generate", action="store_true", help="Generate deploy script")
    parser.add_argument("--list", action="store_true", help="List platforms")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't execute)")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    # 列出平台
    if args.list:
        list_platforms()
        return

    # 检查平台
    if not args.platform:
        print("Error: --platform is required", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # 检查前提条件
    if args.check:
        check_platform(args.platform)
        issues = check_prerequisites(args.platform, args.dir)

        if issues:
            print("\nIssues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n[OK] All prerequisites met!")
        return

    # 生成部署脚本
    if args.generate:
        script = generate_deploy_script(args.platform, args.env)

        if args.output:
            Path(args.output).write_text(script, encoding="utf-8")
            os.chmod(args.output, 0o755)
            print(f"Deploy script saved to: {args.output}")
        else:
            print(script)
        return

    # 执行部署
    deploy(args.platform, args.env, args.dir, args.dry_run)


if __name__ == "__main__":
    main()

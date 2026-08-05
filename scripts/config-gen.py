#!/usr/bin/env python3
"""
DevFlow - Config Generator
Usage:
  python config-gen.py --type docker --dir .
  python config-gen.py --type github-actions --dir .
  python config-gen.py --type all --dir .
"""

import argparse, os, sys
from pathlib import Path
from datetime import datetime

TEMPLATES = {
    "dockerfile_node": '''FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["npm", "start"]
''',
    "dockerfile_python": '''FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
''',
    "dockerfile_java": '''FROM openjdk:17-slim
WORKDIR /app
COPY target/*.jar app.jar
EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
''',
    "github_actions_node": '''name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build
''',
    "github_actions_python": '''name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pip install pytest
      - run: pytest
''',
    "env_example": '''# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# API Keys (不要提交真实值)
API_KEY=your_api_key_here

# 应用配置
PORT=3000
NODE_ENV=development
LOG_LEVEL=info
''',
    "gitignore": '''node_modules/
dist/
build/
.next/
.env
*.log
.DS_Store
__pycache__/
*.pyc
.idea/
.vscode/
coverage/
'''
}

def detect_project_type(dirpath):
    p = Path(dirpath)
    if (p / "package.json").exists():
        return "node"
    elif (p / "requirements.txt").exists() or (p / "pyproject.toml").exists():
        return "python"
    elif (p / "pom.xml").exists() or (p / "build.gradle").exists():
        return "java"
    return None

def main():
    parser = argparse.ArgumentParser(description="Config Generator")
    parser.add_argument("--type", default="all", choices=["dockerfile","github-actions","env","gitignore","all"])
    parser.add_argument("--dir", default=".")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    project_type = detect_project_type(args.dir) or "node"
    output_dir = args.output_dir or args.dir

    generated = []

    if args.type in ("dockerfile", "all"):
        key = f"dockerfile_{project_type}"
        if key in TEMPLATES:
            path = os.path.join(output_dir, "Dockerfile")
            if not os.path.exists(path):
                Path(path).write_text(TEMPLATES[key], encoding="utf-8")
                generated.append("Dockerfile")
            else:
                print(f"跳过: Dockerfile 已存在")

    if args.type in ("github-actions", "all"):
        key = f"github_actions_{project_type}"
        if key in TEMPLATES:
            os.makedirs(os.path.join(output_dir, ".github", "workflows"), exist_ok=True)
            path = os.path.join(output_dir, ".github", "workflows", "ci.yml")
            if not os.path.exists(path):
                Path(path).write_text(TEMPLATES[key], encoding="utf-8")
                generated.append(".github/workflows/ci.yml")
            else:
                print(f"跳过: ci.yml 已存在")

    if args.type in ("env", "all"):
        path = os.path.join(output_dir, ".env.example")
        if not os.path.exists(path):
            Path(path).write_text(TEMPLATES["env_example"], encoding="utf-8")
            generated.append(".env.example")
        else:
            print(f"跳过: .env.example 已存在")

    if args.type in ("gitignore", "all"):
        path = os.path.join(output_dir, ".gitignore")
        if not os.path.exists(path):
            Path(path).write_text(TEMPLATES["gitignore"], encoding="utf-8")
            generated.append(".gitignore")
        else:
            print(f"跳过: .gitignore 已存在")

    if generated:
        print(f"已生成: {', '.join(generated)}")
    else:
        print("无可生成的配置文件（已全部存在）")

if __name__ == "__main__":
    main()

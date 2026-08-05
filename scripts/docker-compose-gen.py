#!/usr/bin/env python3
"""
DevFlow - Docker Compose Generator
生成 Docker Compose 配置
Usage:
  python docker-compose-gen.py --type web
  python docker-compose-gen.py --type fullstack
  python docker-compose-gen.py --type microservices --services api,web,db,redis
  python docker-compose-gen.py --output docker-compose.yml
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

# 预定义的服务模板
SERVICE_TEMPLATES = {
    "web": {
        "image": "nginx:alpine",
        "ports": ["80:80", "443:443"],
        "volumes": ["./nginx.conf:/etc/nginx/nginx.conf:ro"],
        "depends_on": ["api"]
    },
    "api": {
        "image": "node:18-alpine",
        "working_dir": "/app",
        "volumes": ["./api:/app"],
        "command": "npm start",
        "ports": ["3000:3000"],
        "environment": {
            "NODE_ENV": "production",
            "DB_HOST": "db",
            "REDIS_HOST": "redis"
        },
        "depends_on": ["db", "redis"]
    },
    "db": {
        "image": "postgres:15-alpine",
        "ports": ["5432:5432"],
        "environment": {
            "POSTGRES_DB": "app",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "password"
        },
        "volumes": ["postgres_data:/var/lib/postgresql/data"]
    },
    "redis": {
        "image": "redis:7-alpine",
        "ports": ["6379:6379"],
        "volumes": ["redis_data:/data"]
    },
    "mongo": {
        "image": "mongo:6",
        "ports": ["27017:27017"],
        "environment": {
            "MONGO_INITDB_ROOT_USERNAME": "root",
            "MONGO_INITDB_ROOT_PASSWORD": "password"
        },
        "volumes": ["mongo_data:/data/db"]
    },
    "mysql": {
        "image": "mysql:8",
        "ports": ["3306:3306"],
        "environment": {
            "MYSQL_ROOT_PASSWORD": "root",
            "MYSQL_DATABASE": "app",
            "MYSQL_USER": "user",
            "MYSQL_PASSWORD": "password"
        },
        "volumes": ["mysql_data:/var/lib/mysql"]
    },
    "python": {
        "image": "python:3.11-slim",
        "working_dir": "/app",
        "volumes": ["./app:/app"],
        "command": "python main.py",
        "ports": ["8000:8000"],
        "environment": {
            "PYTHONUNBUFFERED": "1"
        }
    },
    "django": {
        "image": "python:3.11-slim",
        "working_dir": "/app",
        "volumes": ["./app:/app"],
        "command": "python manage.py runserver 0.0.0.0:8000",
        "ports": ["8000:8000"],
        "environment": {
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DB_HOST": "db"
        },
        "depends_on": ["db"]
    },
    "flask": {
        "image": "python:3.11-slim",
        "working_dir": "/app",
        "volumes": ["./app:/app"],
        "command": "flask run --host=0.0.0.0",
        "ports": ["5000:5000"],
        "environment": {
            "FLASK_APP": "app.py",
            "FLASK_ENV": "development"
        }
    },
    "go": {
        "image": "golang:1.21-alpine",
        "working_dir": "/app",
        "volumes": ["./app:/app"],
        "command": "go run main.go",
        "ports": ["8080:8080"]
    },
    "elasticsearch": {
        "image": "elasticsearch:8.10.0",
        "ports": ["9200:9200", "9300:9300"],
        "environment": {
            "discovery.type": "single-node",
            "ES_JAVA_OPTS": "-Xms512m -Xmx512m"
        },
        "volumes": ["elasticsearch_data:/usr/share/elasticsearch/data"]
    },
    "kibana": {
        "image": "kibana:8.10.0",
        "ports": ["5601:5601"],
        "environment": {
            "ELASTICSEARCH_HOSTS": "http://elasticsearch:9200"
        },
        "depends_on": ["elasticsearch"]
    },
    "rabbitmq": {
        "image": "rabbitmq:3-management-alpine",
        "ports": ["5672:5672", "15672:15672"],
        "environment": {
            "RABBITMQ_DEFAULT_USER": "guest",
            "RABBITMQ_DEFAULT_PASS": "guest"
        }
    },
    "minio": {
        "image": "minio/minio",
        "ports": ["9000:9000", "9001:9001"],
        "command": "server /data --console-address ':9001'",
        "environment": {
            "MINIO_ROOT_USER": "minioadmin",
            "MINIO_ROOT_PASSWORD": "minioadmin"
        },
        "volumes": ["minio_data:/data"]
    }
}

# 预定义的架构类型
ARCHITECTURE_TYPES = {
    "web": ["web", "api", "db"],
    "fullstack": ["web", "api", "db", "redis"],
    "microservices": ["web", "api", "db", "redis", "mongo"],
    "python": ["python", "db", "redis"],
    "django": ["django", "db", "redis"],
    "flask": ["flask", "db", "redis"],
    "node": ["api", "db", "redis"],
    "go": ["go", "db", "redis"],
    "elk": ["elasticsearch", "kibana"],
    "messaging": ["rabbitmq", "redis"],
    "storage": ["minio", "db"]
}


def generate_service(name: str, config: Dict) -> str:
    """生成单个服务配置"""
    lines = []
    lines.append(f"  {name}:")

    if "image" in config:
        lines.append(f"    image: {config['image']}")

    if "build" in config:
        lines.append(f"    build: {config['build']}")

    if "container_name" in config:
        lines.append(f"    container_name: {config['container_name']}")

    if "working_dir" in config:
        lines.append(f"    working_dir: {config['working_dir']}")

    if "command" in config:
        lines.append(f"    command: {config['command']}")

    if "ports" in config:
        lines.append("    ports:")
        for port in config["ports"]:
            lines.append(f"      - \"{port}\"")

    if "volumes" in config:
        lines.append("    volumes:")
        for volume in config["volumes"]:
            lines.append(f"      - {volume}")

    if "environment" in config:
        lines.append("    environment:")
        for key, value in config["environment"].items():
            lines.append(f"      {key}: {value}")

    if "depends_on" in config:
        lines.append("    depends_on:")
        for dep in config["depends_on"]:
            lines.append(f"      - {dep}")

    if "restart" in config:
        lines.append(f"    restart: {config['restart']}")

    if "networks" in config:
        lines.append("    networks:")
        for network in config["networks"]:
            lines.append(f"      - {network}")

    return "\n".join(lines)


def generate_docker_compose(services: List[str], custom_configs: Dict = None) -> str:
    """生成 Docker Compose 配置"""
    lines = []
    lines.append("version: '3.8'")
    lines.append("")
    lines.append("services:")

    # 生成服务
    for service_name in services:
        if service_name in SERVICE_TEMPLATES:
            config = SERVICE_TEMPLATES[service_name].copy()

            # 应用自定义配置
            if custom_configs and service_name in custom_configs:
                config.update(custom_configs[service_name])

            lines.append(generate_service(service_name, config))
            lines.append("")

    # 生成卷
    volumes = set()
    for service_name in services:
        if service_name in SERVICE_TEMPLATES:
            for volume in SERVICE_TEMPLATES[service_name].get("volumes", []):
                if ":" in volume:
                    vol_name = volume.split(":")[0]
                    if not vol_name.startswith(".") and not vol_name.startswith("/"):
                        volumes.add(vol_name)

    if volumes:
        lines.append("volumes:")
        for volume in sorted(volumes):
            lines.append(f"  {volume}:")
        lines.append("")

    # 生成网络
    lines.append("networks:")
    lines.append("  default:")
    lines.append("    driver: bridge")

    return "\n".join(lines)


def generate_from_requirements(requirements_file: str) -> str:
    """从 requirements.txt 生成配置"""
    services = []

    try:
        content = Path(requirements_file).read_text(encoding="utf-8")

        # 检测框架
        if "django" in content.lower():
            services.append("django")
        elif "flask" in content.lower():
            services.append("flask")
        elif "fastapi" in content.lower():
            services.append("python")

        # 检测数据库
        if "psycopg2" in content or "postgresql" in content:
            services.append("db")
        elif "pymysql" in content or "mysql" in content:
            services.append("mysql")
        elif "pymongo" in content or "mongodb" in content:
            services.append("mongo")

        # 检测缓存
        if "redis" in content.lower():
            services.append("redis")

    except Exception as e:
        print(f"Error reading requirements: {e}", file=sys.stderr)

    if not services:
        services = ["python", "db"]

    return generate_docker_compose(services)


def generate_from_package_json(package_file: str) -> str:
    """从 package.json 生成配置"""
    services = []

    try:
        content = Path(package_file).read_text(encoding="utf-8")
        data = json.loads(content)
        dependencies = data.get("dependencies", {})

        # 检测框架
        if "express" in dependencies:
            services.append("api")
        elif "next" in dependencies:
            services.append("web")
            services.append("api")

        # 检测数据库
        if "pg" in dependencies or "postgres" in dependencies:
            services.append("db")
        elif "mysql2" in dependencies:
            services.append("mysql")
        elif "mongoose" in dependencies:
            services.append("mongo")

        # 检测缓存
        if "redis" in dependencies or "ioredis" in dependencies:
            services.append("redis")

    except Exception as e:
        print(f"Error reading package.json: {e}", file=sys.stderr)

    if not services:
        services = ["api", "db"]

    return generate_docker_compose(services)


def list_services():
    """列出可用服务"""
    print("Available Services:")
    print("=" * 60)
    for name, config in SERVICE_TEMPLATES.items():
        print(f"  {name}: {config.get('image', 'custom')}")
    print("")
    print("Architecture Types:")
    print("=" * 60)
    for name, services in ARCHITECTURE_TYPES.items():
        print(f"  {name}: {', '.join(services)}")


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Docker Compose Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate web stack
  python docker-compose-gen.py --type web

  # Generate fullstack
  python docker-compose-gen.py --type fullstack

  # Generate custom services
  python docker-compose-gen.py --services api,db,redis

  # Generate from requirements.txt
  python docker-compose-gen.py --from-requirements requirements.txt

  # Generate from package.json
  python docker-compose-gen.py --from-package package.json

  # List available services
  python docker-compose-gen.py --list

  # Save to file
  python docker-compose-gen.py --type fullstack --output docker-compose.yml
        """
    )

    parser.add_argument("--type", "-t", choices=list(ARCHITECTURE_TYPES.keys()),
                        help="Architecture type")
    parser.add_argument("--services", "-s", help="Comma-separated list of services")
    parser.add_argument("--from-requirements", help="Generate from requirements.txt")
    parser.add_argument("--from-package", help="Generate from package.json")
    parser.add_argument("--list", action="store_true", help="List available services")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    # 列出服务
    if args.list:
        list_services()
        return

    # 从 requirements.txt 生成
    if args.from_requirements:
        compose = generate_from_requirements(args.from_requirements)
        if args.output:
            Path(args.output).write_text(compose, encoding="utf-8")
            print(f"Docker Compose saved to: {args.output}")
        else:
            print(compose)
        return

    # 从 package.json 生成
    if args.from_package:
        compose = generate_from_package_json(args.from_package)
        if args.output:
            Path(args.output).write_text(compose, encoding="utf-8")
            print(f"Docker Compose saved to: {args.output}")
        else:
            print(compose)
        return

    # 从类型生成
    if args.type:
        services = ARCHITECTURE_TYPES.get(args.type, [])
    elif args.services:
        services = [s.strip() for s in args.services.split(",")]
    else:
        print("Error: --type, --services, --from-requirements, or --from-package is required", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # 生成配置
    compose = generate_docker_compose(services)

    # 输出
    if args.output:
        Path(args.output).write_text(compose, encoding="utf-8")
        print(f"Docker Compose saved to: {args.output}")
    else:
        print(compose)


if __name__ == "__main__":
    main()

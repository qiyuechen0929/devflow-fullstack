#!/usr/bin/env python3
"""
DevFlow - Team Sync Tool
团队配置共享和同步
Usage:
  python team-sync.py --export --team myteam
  python team-sync.py --import --team myteam
  python team-sync.py --init --team myteam
  python team-sync.py --list
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 默认配置目录
CONFIG_DIR = Path.home() / ".devflow" / "teams"
LOCAL_CONFIG = Path(".devflow.json")

# 默认团队配置模板
DEFAULT_TEAM_CONFIG = {
    "version": "1.0.0",
    "team_name": "",
    "created_at": "",
    "updated_at": "",
    "members": [],
    "rules": {
        "security_level": "L4",
        "quality_threshold": 7,
        "max_function_length": 50,
        "max_file_length": 500,
        "require_tests": True,
        "require_docs": True
    },
    "patterns": {
        "allowed": [],
        "blocked": []
    },
    "ignore": [
        "node_modules/",
        "vendor/",
        "*.min.js",
        "*.min.css",
        "dist/",
        "build/"
    ],
    "custom_rules": []
}


def ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_team_config_path(team_name: str) -> Path:
    """获取团队配置文件路径"""
    return CONFIG_DIR / f"{team_name}.json"


def init_team_config(team_name: str) -> Dict:
    """初始化团队配置"""
    ensure_config_dir()

    config = DEFAULT_TEAM_CONFIG.copy()
    config["team_name"] = team_name
    config["created_at"] = datetime.now().isoformat()
    config["updated_at"] = datetime.now().isoformat()

    # 保存配置
    config_path = get_team_config_path(team_name)
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    return config


def load_team_config(team_name: str) -> Optional[Dict]:
    """加载团队配置"""
    config_path = get_team_config_path(team_name)
    if not config_path.exists():
        return None

    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return None


def save_team_config(team_name: str, config: Dict) -> bool:
    """保存团队配置"""
    ensure_config_dir()

    config["updated_at"] = datetime.now().isoformat()
    config_path = get_team_config_path(team_name)

    try:
        config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error saving config: {e}", file=sys.stderr)
        return False


def list_teams() -> List[str]:
    """列出所有团队"""
    ensure_config_dir()
    return [f.stem for f in CONFIG_DIR.glob("*.json")]


def export_config(team_name: str, output_path: str = None) -> str:
    """导出团队配置"""
    config = load_team_config(team_name)
    if not config:
        print(f"Team '{team_name}' not found.", file=sys.stderr)
        return None

    config_json = json.dumps(config, indent=2, ensure_ascii=False)

    if output_path:
        Path(output_path).write_text(config_json, encoding="utf-8")
        print(f"Config exported to: {output_path}")
    else:
        print(config_json)

    return config_json


def import_config(team_name: str, config_path: str) -> bool:
    """导入团队配置"""
    try:
        config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        config["team_name"] = team_name
        config["updated_at"] = datetime.now().isoformat()

        return save_team_config(team_name, config)
    except Exception as e:
        print(f"Error importing config: {e}", file=sys.stderr)
        return False


def sync_to_local(team_name: str) -> bool:
    """同步团队配置到本地项目"""
    config = load_team_config(team_name)
    if not config:
        print(f"Team '{team_name}' not found.", file=sys.stderr)
        return False

    # 生成本地配置
    local_config = {
        "team": team_name,
        "synced_at": datetime.now().isoformat(),
        "rules": config["rules"],
        "patterns": config["patterns"],
        "ignore": config["ignore"]
    }

    try:
        LOCAL_CONFIG.write_text(json.dumps(local_config, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Config synced to {LOCAL_CONFIG}")
        return True
    except Exception as e:
        print(f"Error syncing config: {e}", file=sys.stderr)
        return False


def add_member(team_name: str, member: str) -> bool:
    """添加团队成员"""
    config = load_team_config(team_name)
    if not config:
        config = init_team_config(team_name)

    if member not in config["members"]:
        config["members"].append(member)
        return save_team_config(team_name, config)

    return True


def remove_member(team_name: str, member: str) -> bool:
    """移除团队成员"""
    config = load_team_config(team_name)
    if not config:
        return False

    if member in config["members"]:
        config["members"].remove(member)
        return save_team_config(team_name, config)

    return True


def update_rules(team_name: str, rules: Dict) -> bool:
    """更新团队规则"""
    config = load_team_config(team_name)
    if not config:
        config = init_team_config(team_name)

    config["rules"].update(rules)
    return save_team_config(team_name, config)


def add_custom_rule(team_name: str, rule: Dict) -> bool:
    """添加自定义规则"""
    config = load_team_config(team_name)
    if not config:
        config = init_team_config(team_name)

    config["custom_rules"].append(rule)
    return save_team_config(team_name, config)


def format_team_info(team_name: str, config: Dict) -> str:
    """格式化团队信息"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"Team: {config['team_name']}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Created: {config.get('created_at', 'N/A')}")
    lines.append(f"Updated: {config.get('updated_at', 'N/A')}")
    lines.append("")
    lines.append(f"Members ({len(config.get('members', []))}):")
    for member in config.get("members", []):
        lines.append(f"  - {member}")
    lines.append("")
    lines.append("Rules:")
    for key, value in config.get("rules", {}).items():
        lines.append(f"  - {key}: {value}")
    lines.append("")
    lines.append(f"Ignore Patterns: {len(config.get('ignore', []))}")
    lines.append(f"Custom Rules: {len(config.get('custom_rules', []))}")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="DevFlow Team Sync Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize team config
  python team-sync.py --init --team myteam

  # Export team config
  python team-sync.py --export --team myteam

  # Import team config
  python team-sync.py --import --team myteam --file config.json

  # Sync to local project
  python team-sync.py --sync --team myteam

  # List all teams
  python team-sync.py --list

  # Add member
  python team-sync.py --add-member --team myteam --member john

  # Update rules
  python team-sync.py --update-rules --team myteam --rules '{"security_level": "L3"}'
        """
    )

    parser.add_argument("--init", action="store_true", help="Initialize team config")
    parser.add_argument("--export", action="store_true", help="Export team config")
    parser.add_argument("--import", dest="import_config", action="store_true", help="Import team config")
    parser.add_argument("--sync", action="store_true", help="Sync to local project")
    parser.add_argument("--list", action="store_true", help="List all teams")
    parser.add_argument("--info", action="store_true", help="Show team info")
    parser.add_argument("--add-member", action="store_true", help="Add team member")
    parser.add_argument("--remove-member", action="store_true", help="Remove team member")
    parser.add_argument("--update-rules", action="store_true", help="Update team rules")
    parser.add_argument("--add-rule", action="store_true", help="Add custom rule")

    parser.add_argument("--team", "-t", help="Team name")
    parser.add_argument("--member", "-m", help="Member name")
    parser.add_argument("--file", "-f", help="Config file path")
    parser.add_argument("--rules", help="Rules JSON string")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    # 列出团队
    if args.list:
        teams = list_teams()
        if teams:
            print("Teams:")
            for team in teams:
                print(f"  - {team}")
        else:
            print("No teams found.")
        return

    # 需要团队名称的操作
    if not args.team:
        print("Error: --team is required", file=sys.stderr)
        sys.exit(1)

    # 初始化
    if args.init:
        config = init_team_config(args.team)
        print(f"Team '{args.team}' initialized.")
        print(format_team_info(args.team, config))
        return

    # 导出
    if args.export:
        export_config(args.team, args.output)
        return

    # 导入
    if args.import_config:
        if not args.file:
            print("Error: --file is required for import", file=sys.stderr)
            sys.exit(1)
        if import_config(args.team, args.file):
            print(f"Config imported for team '{args.team}'")
        return

    # 同步到本地
    if args.sync:
        sync_to_local(args.team)
        return

    # 显示信息
    if args.info:
        config = load_team_config(args.team)
        if config:
            print(format_team_info(args.team, config))
        else:
            print(f"Team '{args.team}' not found.")
        return

    # 添加成员
    if args.add_member:
        if not args.member:
            print("Error: --member is required", file=sys.stderr)
            sys.exit(1)
        if add_member(args.team, args.member):
            print(f"Member '{args.member}' added to team '{args.team}'")
        return

    # 移除成员
    if args.remove_member:
        if not args.member:
            print("Error: --member is required", file=sys.stderr)
            sys.exit(1)
        if remove_member(args.team, args.member):
            print(f"Member '{args.member}' removed from team '{args.team}'")
        return

    # 更新规则
    if args.update_rules:
        if not args.rules:
            print("Error: --rules is required", file=sys.stderr)
            sys.exit(1)
        try:
            rules = json.loads(args.rules)
            if update_rules(args.team, rules):
                print(f"Rules updated for team '{args.team}'")
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # 添加自定义规则
    if args.add_rule:
        if not args.rules:
            print("Error: --rules is required", file=sys.stderr)
            sys.exit(1)
        try:
            rule = json.loads(args.rules)
            if add_custom_rule(args.team, rule):
                print(f"Custom rule added to team '{args.team}'")
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # 默认显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()

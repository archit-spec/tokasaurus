#!/usr/bin/env python3
"""
Claude Code Configuration Manager - Manage multiple Claude Code configurations
"""

import json
import os
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml


class ConfigManager:
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or Path.home() / ".claude_configs")
        self.config_dir.mkdir(exist_ok=True)
        self.active_config_file = self.config_dir / "active.json"
    
    def create_config(self, name: str, config: Dict[str, Any]) -> None:
        """Create a new configuration"""
        config_file = self.config_dir / f"{name}.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Configuration '{name}' created at {config_file}")
    
    def list_configs(self) -> List[str]:
        """List all available configurations"""
        configs = []
        for file in self.config_dir.glob("*.json"):
            if file.name != "active.json":
                configs.append(file.stem)
        return configs
    
    def get_config(self, name: str) -> Dict[str, Any]:
        """Get a specific configuration"""
        config_file = self.config_dir / f"{name}.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration '{name}' not found")
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def set_active(self, name: str) -> None:
        """Set the active configuration"""
        if name not in self.list_configs():
            raise ValueError(f"Configuration '{name}' does not exist")
        
        with open(self.active_config_file, 'w') as f:
            json.dump({"active": name}, f)
        print(f"Active configuration set to '{name}'")
    
    def get_active(self) -> Optional[str]:
        """Get the active configuration name"""
        if not self.active_config_file.exists():
            return None
        
        with open(self.active_config_file, 'r') as f:
            return json.load(f).get("active")
    
    def delete_config(self, name: str) -> None:
        """Delete a configuration"""
        config_file = self.config_dir / f"{name}.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration '{name}' not found")
        
        config_file.unlink()
        
        # If this was the active config, clear it
        if self.get_active() == name:
            if self.active_config_file.exists():
                self.active_config_file.unlink()
        
        print(f"Configuration '{name}' deleted")
    
    def export_config(self, name: str, format: str = "json") -> str:
        """Export a configuration to different formats"""
        config = self.get_config(name)
        
        if format.lower() == "yaml":
            return yaml.dump(config, default_flow_style=False)
        elif format.lower() == "env":
            env_vars = []
            for key, value in config.items():
                env_key = f"CLAUDE_{key.upper()}"
                if isinstance(value, list):
                    env_vars.append(f"{env_key}={','.join(map(str, value))}")
                else:
                    env_vars.append(f"{env_key}={value}")
            return "\n".join(env_vars)
        else:
            return json.dumps(config, indent=2)
    
    def import_config(self, name: str, file_path: str) -> None:
        """Import a configuration from a file"""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == ".yaml" or file_path.suffix.lower() == ".yml":
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
        elif file_path.suffix.lower() == ".json":
            with open(file_path, 'r') as f:
                config = json.load(f)
        else:
            raise ValueError("Unsupported file format. Use JSON or YAML.")
        
        self.create_config(name, config)
    
    def show_config(self, name: str) -> None:
        """Display a configuration"""
        config = self.get_config(name)
        print(f"Configuration '{name}':")
        for key, value in config.items():
            print(f"  {key}: {value}")


def create_default_configs(manager: ConfigManager) -> None:
    """Create some default configurations"""
    configs = {
        "development": {
            "max_turns": 20,
            "model": "claude-3-5-sonnet-20241022",
            "system_prompt": "You are a helpful coding assistant focused on development tasks.",
            "allowed_tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            "working_directory": str(Path.cwd())
        },
        "production": {
            "max_turns": 5,
            "model": "claude-3-5-sonnet-20241022",
            "system_prompt": "You are a careful assistant focused on production-ready code.",
            "blocked_tools": ["Bash"],
            "working_directory": str(Path.cwd())
        },
        "analysis": {
            "max_turns": 10,
            "model": "claude-3-5-sonnet-20241022",
            "system_prompt": "You are an expert code analyzer and reviewer.",
            "allowed_tools": ["Read", "Glob", "Grep"],
            "working_directory": str(Path.cwd())
        }
    }
    
    for name, config in configs.items():
        try:
            manager.create_config(name, config)
        except Exception as e:
            print(f"Skipping {name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Claude Code Configuration Manager")
    parser.add_argument("--config-dir", help="Configuration directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new configuration")
    create_parser.add_argument("name", help="Configuration name")
    create_parser.add_argument("--max-turns", type=int, default=10, help="Maximum turns")
    create_parser.add_argument("--model", default="claude-3-5-sonnet-20241022", help="Model to use")
    create_parser.add_argument("--system-prompt", help="System prompt")
    create_parser.add_argument("--allowed-tools", nargs="*", help="Allowed tools")
    create_parser.add_argument("--blocked-tools", nargs="*", help="Blocked tools")
    create_parser.add_argument("--working-directory", help="Working directory")
    
    # List command
    subparsers.add_parser("list", help="List all configurations")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show a configuration")
    show_parser.add_argument("name", help="Configuration name")
    
    # Set active command
    active_parser = subparsers.add_parser("set-active", help="Set active configuration")
    active_parser.add_argument("name", help="Configuration name")
    
    # Get active command
    subparsers.add_parser("get-active", help="Get active configuration")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a configuration")
    delete_parser.add_argument("name", help="Configuration name")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export a configuration")
    export_parser.add_argument("name", help="Configuration name")
    export_parser.add_argument("--format", choices=["json", "yaml", "env"], default="json", help="Export format")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import a configuration")
    import_parser.add_argument("name", help="Configuration name")
    import_parser.add_argument("file", help="File to import from")
    
    # Init command
    subparsers.add_parser("init", help="Initialize with default configurations")
    
    args = parser.parse_args()
    
    manager = ConfigManager(args.config_dir)
    
    try:
        if args.command == "create":
            config = {
                "max_turns": args.max_turns,
                "model": args.model,
                "system_prompt": args.system_prompt,
                "allowed_tools": args.allowed_tools,
                "blocked_tools": args.blocked_tools,
                "working_directory": args.working_directory or str(Path.cwd())
            }
            # Remove None values
            config = {k: v for k, v in config.items() if v is not None}
            manager.create_config(args.name, config)
        
        elif args.command == "list":
            configs = manager.list_configs()
            active = manager.get_active()
            print("Available configurations:")
            for config in configs:
                marker = " (active)" if config == active else ""
                print(f"  {config}{marker}")
        
        elif args.command == "show":
            manager.show_config(args.name)
        
        elif args.command == "set-active":
            manager.set_active(args.name)
        
        elif args.command == "get-active":
            active = manager.get_active()
            if active:
                print(f"Active configuration: {active}")
            else:
                print("No active configuration set")
        
        elif args.command == "delete":
            manager.delete_config(args.name)
        
        elif args.command == "export":
            output = manager.export_config(args.name, args.format)
            print(output)
        
        elif args.command == "import":
            manager.import_config(args.name, args.file)
        
        elif args.command == "init":
            create_default_configs(manager)
            print("Default configurations created")
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
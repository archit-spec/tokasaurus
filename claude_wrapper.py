#!/usr/bin/env python3
"""
Claude Code SDK Wrapper - A convenient CLI tool for Claude Code SDK operations
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import anyio

try:
    from claude_code_sdk import query, ClaudeCodeOptions
except ImportError:
    print("Error: claude-code-sdk not installed. Run: pip install claude-code-sdk")
    sys.exit(1)


class ClaudeWrapper:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or str(Path.home() / ".claude_wrapper_config.json")
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "max_turns": 10,
                "model": "claude-3-5-sonnet-20241022",
                "system_prompt": None,
                "working_directory": str(Path.cwd()),
                "allowed_tools": None,
                "blocked_tools": None
            }
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    async def query_claude(self, prompt: str, **kwargs) -> None:
        """Query Claude Code with the given prompt"""
        options = ClaudeCodeOptions(
            max_turns=kwargs.get('max_turns', self.config.get('max_turns', 10)),
            model=kwargs.get('model', self.config.get('model')),
            system_prompt=kwargs.get('system_prompt', self.config.get('system_prompt')),
            working_directory=kwargs.get('working_directory', self.config.get('working_directory')),
            allowed_tools=kwargs.get('allowed_tools', self.config.get('allowed_tools')),
            blocked_tools=kwargs.get('blocked_tools', self.config.get('blocked_tools'))
        )
        
        async for message in query(prompt=prompt, options=options):
            print(message, end='', flush=True)
    
    def configure(self, **kwargs):
        """Update configuration"""
        for key, value in kwargs.items():
            if value is not None:
                self.config[key] = value
        self.save_config()
        print(f"Configuration updated and saved to {self.config_path}")
    
    def show_config(self):
        """Display current configuration"""
        print("Current Configuration:")
        for key, value in self.config.items():
            print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(description="Claude Code SDK Wrapper")
    parser.add_argument("--config", help="Path to config file")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query Claude Code")
    query_parser.add_argument("prompt", help="Prompt to send to Claude")
    query_parser.add_argument("--max-turns", type=int, help="Maximum conversation turns")
    query_parser.add_argument("--model", help="Model to use")
    query_parser.add_argument("--system-prompt", help="System prompt")
    query_parser.add_argument("--working-directory", help="Working directory")
    query_parser.add_argument("--allowed-tools", nargs="*", help="Allowed tools")
    query_parser.add_argument("--blocked-tools", nargs="*", help="Blocked tools")
    
    # Configure command
    config_parser = subparsers.add_parser("config", help="Configure settings")
    config_parser.add_argument("--max-turns", type=int, help="Default maximum turns")
    config_parser.add_argument("--model", help="Default model")
    config_parser.add_argument("--system-prompt", help="Default system prompt")
    config_parser.add_argument("--working-directory", help="Default working directory")
    config_parser.add_argument("--show", action="store_true", help="Show current configuration")
    
    args = parser.parse_args()
    
    wrapper = ClaudeWrapper(args.config)
    
    if args.command == "query":
        query_kwargs = {
            k.replace('-', '_'): v for k, v in vars(args).items() 
            if v is not None and k not in ['command', 'config', 'prompt']
        }
        anyio.run(wrapper.query_claude, args.prompt, **query_kwargs)
    
    elif args.command == "config":
        if args.show:
            wrapper.show_config()
        else:
            config_kwargs = {
                k.replace('-', '_'): v for k, v in vars(args).items() 
                if v is not None and k not in ['command', 'config', 'show']
            }
            wrapper.configure(**config_kwargs)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
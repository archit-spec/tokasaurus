#!/usr/bin/env python3
"""
Claude Code TUI - Terminal User Interface for Claude Code SDK
"""

import asyncio
import sys
import base64
import tempfile
from pathlib import Path
from typing import List, Optional

try:
    import anyio
    from claude_code_sdk import query, ClaudeCodeOptions
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.layout import Layout
    from rich.align import Align
    import subprocess
    from PIL import Image
    import io
    import keyboard
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install claude-code-sdk rich pillow keyboard")
    sys.exit(1)


class ClaudeTUI:
    def __init__(self):
        self.console = Console()
        self.conversation_history: List[str] = []
        self.options = ClaudeCodeOptions(
            max_turns=10,
            permission_mode="bypassPermissions"  # Allow all tools including Read
        )
        self.clipboard_paste_pending = False
    
    def get_clipboard_image(self) -> Optional[str]:
        """Get image from clipboard and save to temp file"""
        try:
            # Try different clipboard tools based on platform
            if sys.platform == "linux":
                # Try xclip first
                try:
                    result = subprocess.run(
                        ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
                        capture_output=True,
                        check=True
                    )
                    if result.stdout:
                        # Save to temp file
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                            f.write(result.stdout)
                            return f.name
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
                
                # Try wl-paste for Wayland
                try:
                    result = subprocess.run(
                        ["wl-paste", "--type", "image/png"],
                        capture_output=True,
                        check=True
                    )
                    if result.stdout:
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                            f.write(result.stdout)
                            return f.name
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
            
            elif sys.platform == "darwin":
                # macOS - use pngpaste
                try:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                        subprocess.run(["pngpaste", f.name], check=True)
                        return f.name
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
            
            elif sys.platform == "win32":
                # Windows - use PowerShell
                try:
                    ps_script = """
                    Add-Type -AssemblyName System.Windows.Forms
                    if ([System.Windows.Forms.Clipboard]::ContainsImage()) {
                        $image = [System.Windows.Forms.Clipboard]::GetImage()
                        $image.Save('temp_clipboard.png', [System.Drawing.Imaging.ImageFormat]::Png)
                        Write-Output 'temp_clipboard.png'
                    }
                    """
                    result = subprocess.run(
                        ["powershell", "-Command", ps_script],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    if result.stdout.strip() == "temp_clipboard.png":
                        return "temp_clipboard.png"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
            
            return None
        except Exception:
            return None
    
    def display_banner(self):
        """Display the application banner"""
        banner = """
╔═══════════════════════════════════════╗
║           Claude Code TUI             ║
║     Terminal Interface for Claude     ║
╚═══════════════════════════════════════╝
        """
        self.console.print(banner, style="bold blue")
        self.console.print("Type 'help' for commands or 'quit' to exit\n")
    
    def display_help(self):
        """Display help information"""
        help_text = """
## Commands

- `help` - Show this help message
- `quit` or `exit` - Exit the application
- `clear` - Clear conversation history
- `config` - Show current configuration
- `set max_turns <n>` - Set maximum conversation turns
- `image <path>` - Include an image from file path
- `paste` - Include image from clipboard
- Any other text will be sent to Claude

## Tips

- Responses are rendered as markdown
- Use Ctrl+C to interrupt long responses
- Claude has access to file system tools
- For images: `image /path/to/image.png What do you see?`
- For clipboard: `paste What's in this screenshot?` or **Ctrl+Shift+V**
        """
        self.console.print(Panel(Markdown(help_text), title="Help", border_style="green"))
    
    def display_config(self):
        """Display current configuration"""
        config_text = f"""
## Current Configuration

- **Max Turns**: {self.options.max_turns}
- **Model**: {getattr(self.options, 'model', 'claude-sonnet-4-20250514')}
- **Working Directory**: {getattr(self.options, 'cwd', 'current')}
        """
        self.console.print(Panel(Markdown(config_text), title="Configuration", border_style="blue"))
    
    async def send_query(self, prompt: str) -> str:
        """Send query to Claude and return response"""
        response_parts = []
        
        with Live(Spinner("dots", text="Claude is thinking..."), console=self.console) as live:
            try:
                async for message in query(prompt=prompt, options=self.options):
                    if hasattr(message, 'content') and hasattr(message.content, '__iter__'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                response_parts.append(block.text)
                                # Update live display with partial response
                                live.update(Markdown('\n'.join(response_parts)))
                    elif hasattr(message, 'result'):
                        response_parts.append(message.result)
                        live.update(Markdown('\n'.join(response_parts)))
            except KeyboardInterrupt:
                live.stop()
                self.console.print("\n[yellow]Response interrupted by user[/yellow]")
                return '\n'.join(response_parts) if response_parts else "Interrupted"
            except Exception as e:
                live.stop()
                self.console.print(f"[red]Error: {e}[/red]")
                return f"Error: {e}"
        
        return '\n'.join(response_parts)
    
    def process_command(self, user_input: str) -> bool:
        """Process user commands. Returns True to continue, False to quit"""
        user_input = user_input.strip()
        
        if user_input.lower() in ['quit', 'exit']:
            return False
        
        elif user_input.lower() == 'help':
            self.display_help()
            return True
        
        elif user_input.lower() == 'clear':
            self.conversation_history.clear()
            self.console.clear()
            self.display_banner()
            self.console.print("[green]Conversation history cleared[/green]")
            return True
        
        elif user_input.lower() == 'config':
            self.display_config()
            return True
        
        elif user_input.lower().startswith('set max_turns '):
            try:
                turns = int(user_input.split()[-1])
                self.options = ClaudeCodeOptions(
                    max_turns=turns,
                    permission_mode="bypassPermissions"
                )
                self.console.print(f"[green]Max turns set to {turns}[/green]")
            except ValueError:
                self.console.print("[red]Invalid number for max_turns[/red]")
            return True
        
        elif user_input.lower().startswith('image '):
            # Handle image command
            parts = user_input.split(' ', 2)
            if len(parts) < 2:
                self.console.print("[red]Usage: image <path> [question][/red]")
                return True
            
            image_path = parts[1]
            prompt = parts[2] if len(parts) > 2 else "What do you see in this image?"
            
            # Check if image exists
            path = Path(image_path)
            if not path.exists():
                self.console.print(f"[red]Image not found: {image_path}[/red]")
                return True
            
            # Create prompt with image reference
            full_prompt = f"Analyze this image: {image_path}\n\n{prompt}"
            
            # Process as Claude query
            self.pending_query = full_prompt
            return None
        
        elif user_input.lower().startswith('paste'):
            # Handle clipboard image
            parts = user_input.split(' ', 1)
            prompt = parts[1] if len(parts) > 1 else "What do you see in this image?"
            
            self.console.print("[yellow]Getting image from clipboard...[/yellow]")
            clipboard_image = self.get_clipboard_image()
            
            if not clipboard_image:
                self.console.print("[red]No image found in clipboard or clipboard tool not available[/red]")
                self.console.print("[yellow]Install: xclip (Linux), pngpaste (macOS)[/yellow]")
                return True
            
            self.console.print(f"[green]Got clipboard image: {clipboard_image}[/green]")
            
            # Create prompt with image reference
            full_prompt = f"Analyze this image: {clipboard_image}\n\n{prompt}"
            
            # Process as Claude query
            self.pending_query = full_prompt
            return None
        
        else:
            # It's a query for Claude
            return None  # Signal to handle as Claude query
    
    def setup_keyboard_listener(self):
        """Setup keyboard listener for Ctrl+Shift+V"""
        def on_ctrl_shift_v():
            self.clipboard_paste_pending = True
            self.console.print("\n[yellow]📋 Clipboard paste detected! Processing image...[/yellow]")
        
        try:
            keyboard.add_hotkey('ctrl+shift+v', on_ctrl_shift_v)
        except Exception:
            pass  # Keyboard hooks might not work in all environments
    
    async def run(self):
        """Main application loop"""
        self.display_banner()
        self.setup_keyboard_listener()
        
        while True:
            try:
                # Check for pending clipboard paste
                if self.clipboard_paste_pending:
                    self.clipboard_paste_pending = False
                    
                    clipboard_image = self.get_clipboard_image()
                    if clipboard_image:
                        self.console.print(f"[green]✓ Got clipboard image: {clipboard_image}[/green]")
                        follow_up = Prompt.ask("[bold green]What would you like to know about this image?[/bold green]", 
                                             default="What do you see in this image?", console=self.console)
                        
                        user_input = f"Analyze this image: {clipboard_image}\n\n{follow_up}"
                        
                        # Send to Claude
                        self.console.print(f"\n[bold blue]Claude[/bold blue]:")
                        response = await self.send_query(user_input)
                        
                        # Display response
                        if response and response != "Interrupted":
                            try:
                                markdown_response = Markdown(response)
                                self.console.print(Panel(markdown_response, border_style="blue"))
                            except Exception:
                                self.console.print(Panel(response, border_style="blue"))
                        
                        # Add to history
                        self.conversation_history.append(f"User: [Image] {follow_up}")
                        self.conversation_history.append(f"Claude: {response}")
                        continue
                    else:
                        self.console.print("[red]❌ No image found in clipboard[/red]")
                
                # Get user input
                user_input = Prompt.ask("\n[bold green]You[/bold green]", console=self.console)
                
                if not user_input.strip():
                    continue
                
                # Process commands
                command_result = self.process_command(user_input)
                if command_result is False:
                    break
                elif command_result is True:
                    continue
                
                # Send to Claude
                self.console.print(f"\n[bold blue]Claude[/bold blue]:")
                
                # Check if we have a pending query from image/paste command
                query_text = getattr(self, 'pending_query', user_input)
                if hasattr(self, 'pending_query'):
                    delattr(self, 'pending_query')
                
                response = await self.send_query(query_text)
                
                # Display response with markdown rendering
                if response and response != "Interrupted":
                    try:
                        markdown_response = Markdown(response)
                        self.console.print(Panel(markdown_response, border_style="blue"))
                    except Exception:
                        # Fallback to plain text if markdown fails
                        self.console.print(Panel(response, border_style="blue"))
                
                # Add to history
                self.conversation_history.append(f"User: {user_input}")
                self.conversation_history.append(f"Claude: {response}")
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'quit' to exit cleanly[/yellow]")
                continue
            except EOFError:
                break
        
        self.console.print("\n[bold blue]Goodbye![/bold blue]")


def main():
    """Entry point"""
    try:
        tui = ClaudeTUI()
        anyio.run(tui.run)
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
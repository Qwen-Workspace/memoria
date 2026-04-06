"""
CLI/TUI Interface for AI Terminal Assistant
Interactive terminal interface with rich formatting
"""
import asyncio
from typing import Optional, Dict, List
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.styles import Style

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

try:
    from .router import Router
    from .config import Config
    from .models import ActionType
except ImportError:
    from router import Router
    from config import Config
    from models import ActionType


# Custom key bindings
bindings = KeyBindings()

@bindings.add('c-c')
def _(event):
    """Handle Ctrl+C"""
    event.app.exit(exception=KeyboardInterrupt())

@bindings.add('c-d')
def _(event):
    """Handle Ctrl+D for dry-run toggle"""
    event.app.exit(result='dry_run')


class CommandCompleter(Completer):
    """Auto-completion for commands"""
    
    def __init__(self, commands: List[str]):
        self.commands = commands
    
    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor()
        for command in self.commands:
            if command.startswith(word):
                yield Completion(command, start_position=-len(word))


class CLIInterface:
    """Interactive CLI interface with rich formatting"""
    
    def __init__(self, config: Config):
        self.config = config
        self.router = Router(config)
        self.console = Console()
        self.running = True
        
        # Setup prompt session
        history_path = Path(config.ui.history_path).expanduser()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.session = PromptSession(
            history=FileHistory(str(history_path)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=CommandCompleter(['/help', '/mode', '/status', '/clear', '/quit']),
            key_bindings=bindings,
        )
        
        # Style configuration
        self.style = Style.from_dict({
            'prompt': 'ansicyan bold',
            'thought': 'ansiyellow italic',
            'success': 'ansigreen',
            'error': 'ansired bold',
            'warning': 'ansiyellow',
            'info': 'ansiblue',
        })
    
    def print_header(self):
        """Print application header"""
        header = Text()
        header.append("🤖 AI Terminal Assistant", style="bold magenta")
        header.append(f" | Mode: {self.config.security.mode}", style="dim")
        header.append(f" | Root: {self.config.security.allowed_root}", style="dim")
        
        self.console.print(Panel(header, border_style="magenta"))
        self.console.print()
    
    def print_thought(self, thought: str):
        """Print AI's thought process"""
        self.console.print(Panel(
            Markdown(thought),
            title="💭 Thought",
            border_style="yellow",
            title_align="left"
        ))
    
    def print_action_result(self, result: Dict):
        """Print action execution result"""
        action = result.get('action', {})
        action_type = action.get('type', 'unknown')
        path = action.get('path', '')
        status = result.get('status', 'unknown')
        message = result.get('message', '')
        
        # Icon based on action type
        icons = {
            'read_file': '📖',
            'write_file': '✍️',
            'append_file': '➕',
            'delete_file': '🗑️',
            'rename_file': '🔄',
            'list_dir': '📁'
        }
        icon = icons.get(action_type, '⚙️')
        
        # Color based on status
        status_colors = {
            'executed': 'green',
            'denied': 'red',
            'pending_confirmation': 'yellow',
            'failed': 'red'
        }
        color = status_colors.get(status, 'white')
        
        # Build status text
        status_text = Text()
        status_text.append(f"{icon} ", style="")
        status_text.append(f"[{action_type}] ", style="bold")
        status_text.append(f"{path} ", style="dim")
        status_text.append(f"→ {status}", style=f"bold {color}")
        
        self.console.print(status_text)
        
        # Show additional details
        if message and status != 'pending_confirmation':
            self.console.print(f"   {message}", style="dim")
        
        # Show content for read operations
        if result.get('content') and action_type == 'read_file':
            content = result['content']
            try:
                syntax = Syntax(content, "python", theme="monokai", line_numbers=True)
                self.console.print(Panel(syntax, border_style="blue", title="Content"))
            except:
                self.console.print(Panel(content, border_style="blue", title="Content"))
        
        # Show backup info
        if result.get('backup_path'):
            self.console.print(f"   💾 Backup: {result['backup_path']}", style="dim italic")
        
        # Show error if failed
        if result.get('error'):
            self.console.print(f"   ❌ Error: {result['error']}", style="red")
        
        self.console.print()
    
    async def print_confirmation_prompt(self, result: Dict) -> bool:
        """Prompt user for confirmation"""
        action = result.get('action', {})
        action_type = action.get('type', 'unknown')
        path = action.get('path', '')
        reason = result.get('reason', '')
        
        self.console.print()
        self.console.print(f"⚠️  Action requires confirmation:", style="bold yellow")
        self.console.print(f"   Type: {action_type}", style="dim")
        self.console.print(f"   Path: {path}", style="dim")
        
        if reason:
            self.console.print(f"   Reason: {reason}", style="italic")
        
        # Show content preview for write operations
        if action.get('content'):
            content = action['content']
            preview = content[:500] + "..." if len(content) > 500 else content
            self.console.print(Panel(preview, title="Preview", border_style="yellow"))
        
        self.console.print()
        
        # Get user input asynchronously
        try:
            response = await self.session.prompt_async(
                [('class:warning', 'Confirm? [y/n/dry-run]: ')],
                style=self.style
            )
            response = response.strip().lower()
            return response in ['y', 'yes']
        except EOFError:
            return False
    
    def print_error(self, message: str):
        """Print error message"""
        self.console.print(f"❌ {message}", style="bold red")
    
    def print_status(self):
        """Print current status"""
        context = self.router.get_context_summary()
        
        table = Table(title="Session Status", border_style="blue")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Session ID", context['session_id'])
        table.add_row("Messages", str(context['message_count']))
        table.add_row("Security Mode", context['security_mode'])
        table.add_row("Allowed Root", context['allowed_root'])
        table.add_row("Max File Size", f"{context['max_file_size_mb']} MB")
        
        self.console.print(table)
    
    def print_help(self):
        """Print help information"""
        help_text = """
# Commands

- `/help` - Show this help message
- `/status` - Show current session status
- `/mode <mode>` - Change security mode (dry_run, interactive, scoped_auto)
- `/clear` - Clear conversation history
- `/quit` or `/exit` - Exit the application

# Usage

Type your natural language prompt and press Enter. The AI will propose actions 
which may require your confirmation depending on the security mode.

# Security Modes

- **dry_run**: Show what would happen without executing
- **interactive**: Require confirmation for each action (default)
- **scoped_auto**: Auto-execute read operations, confirm writes/deletes
"""
        self.console.print(Markdown(help_text))
    
    def handle_command(self, command: str) -> bool:
        """
        Handle special commands
        Returns True if should continue running, False to exit
        """
        parts = command.strip().split()
        cmd = parts[0].lower() if parts else ''
        
        if cmd in ['/quit', '/exit', '/q']:
            self.running = False
            return False
        
        elif cmd == '/help':
            self.print_help()
        
        elif cmd == '/status':
            self.print_status()
        
        elif cmd == '/clear':
            self.router.clear_history()
            self.console.print("✓ Conversation history cleared", style="green")
        
        elif cmd == '/mode':
            if len(parts) < 2:
                self.console.print(f"Current mode: {self.config.security.mode}", style="yellow")
                self.console.print("Usage: /mode <dry_run|interactive|scoped_auto>", style="dim")
            else:
                new_mode = parts[1]
                if new_mode in ['dry_run', 'interactive', 'scoped_auto']:
                    self.config.security.mode = new_mode
                    self.console.print(f"✓ Mode changed to: {new_mode}", style="green")
                else:
                    self.print_error(f"Invalid mode: {new_mode}")
        
        else:
            self.print_error(f"Unknown command: {cmd}. Type /help for assistance.")
        
        return True
    
    async def process_user_input(self, user_input: str):
        """Process user input through the router"""
        if not user_input.strip():
            return
        
        # Check for commands
        if user_input.startswith('/'):
            if not self.handle_command(user_input):
                return
        else:
            # Process as normal prompt
            with self.console.status("[bold green]Thinking...", spinner="dots"):
                result = await self.router.process_prompt(user_input)
            
            if result.get('success'):
                # Print thought
                if result.get('thought'):
                    self.print_thought(result['thought'])
                
                # Process each action
                pending_actions = []
                executed_results = []
                for action_result in result.get('actions', []):
                    self.print_action_result(action_result)
                    
                    # Collect pending confirmations
                    if action_result.get('status') == 'pending_confirmation':
                        pending_actions.append(action_result)
                    elif action_result.get('status') == 'executed':
                        executed_results.append(action_result)
                
                # Handle confirmations
                for pending in pending_actions:
                    confirmed = await self.print_confirmation_prompt(pending)
                    confirm_result = self.router.confirm_action(
                        pending['action'],
                        confirmed
                    )
                    
                    status_icon = "✓" if confirmed else "✗"
                    status_color = "green" if confirmed else "red"
                    self.console.print(
                        f"   {status_icon} Confirmation: {confirm_result['message']}",
                        style=status_color
                    )
                    
                    if confirmed and confirm_result.get('status') == 'executed':
                        executed_results.append({
                            'action': pending['action'],
                            'status': 'executed',
                            'content': confirm_result.get('content'),
                            'message': confirm_result.get('message')
                        })
                
                # If there were executed read operations, send results back to AI for response
                if executed_results:
                    read_contents = [
                        r for r in executed_results 
                        if r['action'].get('type') == 'read_file' and r.get('content')
                    ]
                    
                    if read_contents:
                        # Build summary of what was read
                        summary_parts = []
                        for read_result in read_contents:
                            path = read_result['action'].get('path', 'unknown')
                            content = read_result.get('content', '')
                            summary_parts.append(f"Arquivo {path}:\n{content}")
                        
                        summary = "\n\n".join(summary_parts)
                        
                        # Send back to AI to generate response
                        followup_prompt = f"Com base no conteúdo lido dos arquivos, responda à pergunta do usuário.\n\n{summary}"
                        
                        with self.console.status("[bold green]Generating response...", spinner="dots"):
                            followup_result = await self.router.process_prompt(followup_prompt)
                        
                        if followup_result.get('success') and followup_result.get('thought'):
                            self.print_thought(followup_result['thought'])
                            
                            # Execute any follow-up actions if needed
                            for action_result in followup_result.get('actions', []):
                                self.print_action_result(action_result)
            else:
                self.print_error(result.get('error', 'Unknown error'))
    
    async def run(self):
        """Main application loop"""
        self.print_header()
        self.print_help()
        
        while self.running:
            try:
                # Get user input
                user_input = await self.session.prompt_async(
                    [('class:prompt', '🤖 '), ('', '')],
                    style=self.style
                )
                
                # Process input
                await self.process_user_input(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\nUse /quit to exit or Ctrl+C again to force quit", style="yellow")
            except EOFError:
                break
            except Exception as e:
                self.print_error(f"Unexpected error: {e}")
        
        self.console.print("\n👋 Goodbye!", style="bold magenta")


async def main():
    """Entry point for CLI"""
    config = Config.load_with_env()
    cli = CLIInterface(config)
    await cli.run()


if __name__ == '__main__':
    asyncio.run(main())

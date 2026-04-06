# AI Terminal Assistant

🤖 Secure CLI assistant for file system operations with AI guidance.

## ⚠️ Security Warning

This system grants an AI model the ability to read and write local files. **By default, all actions require human review.** Never run in unrestricted autonomous mode without sandboxing, backups, and auditing.

## 🎯 Features

- **Multi-Provider AI Support**: Ollama (local), OpenAI, Anthropic
- **Security-First Design**: Path traversal prevention, allowlists, size limits
- **Three Operation Modes**:
  - `dry_run`: Preview actions without execution
  - `interactive`: Confirm each action (default)
  - `scoped_auto`: Auto-execute reads, confirm writes/deletes
- **Automatic Backups**: All modifications create timestamped backups
- **Audit Logging**: Complete trail of all prompts and actions
- **Rich CLI Interface**: Syntax highlighting, interactive confirmations, command history

## 📦 Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install pydantic pyyaml python-dotenv rich prompt_toolkit litellm httpx structlog
```

## 🚀 Quick Start

### 1. Configure Your Model

Edit `config.yaml` to set your preferred AI provider:

**For Ollama (Local):**
```yaml
model:
  provider: ollama
  name: llama3.1
  api_base: http://localhost:11434
```

**For OpenAI:**
```yaml
model:
  provider: openai
  name: gpt-3.5-turbo
  api_key_env: OPENAI_API_KEY
```

**For Anthropic:**
```yaml
model:
  provider: anthropic
  name: claude-3-sonnet-20240229
  api_key_env: ANTHROPIC_API_KEY
```

### 2. Set Environment Variables

```bash
export OPENAI_API_KEY=your-key-here  # If using OpenAI
export ANTHROPIC_API_KEY=your-key-here  # If using Anthropic
```

### 3. Run the Application

```bash
python main.py
```

## 💻 Usage

### Basic Commands

Once running, you can:

1. **Type natural language prompts:**
   ```
   🤖 Create a Python file with a hello world function
   ```

2. **Use special commands:**
   - `/help` - Show help message
   - `/status` - Display session status
   - `/mode <mode>` - Change security mode
   - `/clear` - Clear conversation history
   - `/quit` - Exit application

3. **Confirm or deny actions:**
   - `y` or `yes` - Approve action
   - `n` or `no` - Deny action
   - `dry-run` - Preview without executing

### Example Session

```
🤖 AI Terminal Assistant | Mode: interactive | Root: ./workspace

Type your prompt:
🤖 Create a utility file with a function to calculate fibonacci numbers

💭 Thought: I'll create a new Python module with an efficient fibonacci implementation

✍️ [write_file] src/fibonacci.py → pending_confirmation
   Reason: Create new utility module

⚠️  Action requires confirmation:
   Type: write_file
   Path: src/fibonacci.py
   Reason: Create new utility module

Preview:
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

Confirm? [y/n/dry-run]: y
   ✓ Confirmation: Successfully wrote file (156 bytes)
```

## 🔒 Security Model

### Path Validation
- All paths resolved to absolute paths
- Path traversal (`..`) blocked
- Only files within `allowed_root` accessible
- Blocked directories: `.git`, `.venv`, `__pycache__`, `node_modules`

### File Operations
| Operation | Behavior |
|-----------|----------|
| Read | Returns content + metadata |
| Write | Creates/overwrites with automatic backup |
| Append | Adds to end without altering existing content |
| Rename | Validates destination, prevents accidental overwrite |
| Delete | Requires explicit confirmation, creates backup |
| List | Returns directory structure with depth limit |

### Operation Modes

**Dry Run (Safest)**
```bash
/mode dry_run
```
Shows what would happen without any execution.

**Interactive (Default)**
```bash
/mode interactive
```
Requires confirmation for every action.

**Scoped Auto**
```bash
/mode scoped_auto
```
Auto-executes read operations, requires confirmation for writes/deletes.

## 📁 Project Structure

```
ai-terminal-assistant/
├── main.py              # Entry point
├── config.yaml          # Configuration file
├── src/
│   ├── __init__.py      # Package exports
│   ├── models.py        # Pydantic models & schemas
│   ├── config.py        # Configuration manager
│   ├── security.py      # Security engine & validation
│   ├── fs_executor.py   # Safe file system operations
│   ├── ai_adapter.py    # AI provider adapters
│   ├── router.py        # Request orchestration
│   └── cli.py           # CLI/TUI interface
├── logs/
│   └── audit.jsonl      # Audit log
└── workspace/           # Default allowed root
```

## 📊 Audit Logging

All operations are logged to `logs/audit.jsonl` with:
- Timestamp
- Session ID
- Prompt hash
- Action details
- Status (pending/approved/denied/executed/failed)
- Metadata (backup paths, error messages)

Example entry:
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "session_id": "20240115_103000",
  "prompt_hash": "abc123...",
  "action_type": "write_file",
  "path": "src/utils.py",
  "status": "executed",
  "message": "Successfully wrote file",
  "metadata": {
    "backup_path": "src/utils.py.bak.20240115_103000"
  }
}
```

## ⚙️ Configuration Options

### Model Settings
| Option | Description | Default |
|--------|-------------|---------|
| `provider` | AI provider (ollama/openai/anthropic) | ollama |
| `name` | Model identifier | llama3.1 |
| `api_base` | API endpoint URL | localhost:11434 |
| `temperature` | Response creativity (0-2) | 0.7 |
| `max_tokens` | Maximum response length | 2048 |

### Security Settings
| Option | Description | Default |
|--------|-------------|---------|
| `mode` | Security mode | interactive |
| `allowed_root` | Base directory for operations | ./workspace |
| `max_file_size_mb` | Maximum file size | 50 |
| `blocked_paths` | Forbidden directories | [.git, .venv, ...] |

## 🛠️ Development

### Running Tests
```bash
pytest tests/
```

### Adding New AI Providers

1. Create adapter in `src/ai_adapter.py`:
```python
class CustomAdapter(BaseAIAdapter):
    async def chat(self, messages, system_prompt) -> AIResponse:
        # Implement API call
        pass
```

2. Register in factory:
```python
adapters = {
    "custom": CustomAdapter,
    # ...
}
```

## 📝 Roadmap

- [ ] MVP: CLI basic + AI adapter + dry-run + safe reading
- [ ] v0.2: Write executor + interactive confirmation + audit logs
- [ ] v0.3: Advanced configuration + allowlists + automatic backups
- [ ] v0.4: Scoped auto mode + Git integration + visual diffs
- [ ] v1.0: Optional sandboxing + plugin system + complete documentation

## 📄 License

MIT License - See LICENSE file for details.

## ⚠️ Disclaimer

This tool provides powerful file system access to an AI model. Always:
1. Review proposed actions before confirming
2. Use in isolated environments for sensitive work
3. Maintain regular backups
4. Monitor audit logs regularly

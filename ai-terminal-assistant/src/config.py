"""
Configuration Manager for AI Terminal Assistant
Loads and validates configuration from YAML and environment variables
"""
import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import yaml
from dotenv import load_dotenv


class ModelConfig(BaseModel):
    """AI Model configuration"""
    provider: str = Field(default="ollama", description="AI provider (openai, anthropic, ollama, etc.)")
    name: str = Field(default="llama3.1", description="Model name/identifier")
    api_base: Optional[str] = Field(None, description="API base URL for local models")
    api_key_env: Optional[str] = Field(None, description="Environment variable name for API key")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, description="Maximum tokens in response")


class SecurityConfig(BaseModel):
    """Security and permissions configuration"""
    mode: str = Field(default="interactive", description="Security mode: dry_run, interactive, scoped_auto")
    allowed_root: str = Field(default="./workspace", description="Root directory for file operations")
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    require_git_backup: bool = Field(default=True, description="Require git backup before modifications")
    allowed_extensions: Optional[List[str]] = Field(None, description="Allowed file extensions")
    blocked_paths: List[str] = Field(default_factory=lambda: [".git", ".venv", "__pycache__", "node_modules"])
    restrict_to_workspace: bool = Field(default=True, description="Restrict all operations to workspace directory only")


class UIConfig(BaseModel):
    """User interface configuration"""
    theme: str = Field(default="dark", description="UI theme: dark, light")
    show_diffs: bool = Field(default=True, description="Show diffs before applying changes")
    history_path: str = Field(default="~/.config/ai-cli/history", description="Path to command history")
    syntax_highlighting: bool = Field(default=True, description="Enable syntax highlighting")


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Logging level")
    audit_path: str = Field(default="./logs/audit.jsonl", description="Path to audit log file")
    structured: bool = Field(default=True, description="Use structured logging")


class Config(BaseModel):
    """Main configuration class"""
    model: ModelConfig = Field(default_factory=ModelConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @field_validator('security')
    @classmethod
    def validate_security_config(cls, v: SecurityConfig) -> SecurityConfig:
        """Validate security configuration"""
        if v.mode not in ["dry_run", "interactive", "scoped_auto"]:
            raise ValueError(f"Invalid security mode: {v.mode}")
        return v
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'Config':
        """Load configuration from YAML file"""
        path = Path(config_path)
        if not path.exists():
            return cls()  # Return default config
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        return cls(**data)
    
    @classmethod
    def load_with_env(cls, config_path: Optional[str] = None) -> 'Config':
        """Load configuration from file and environment variables"""
        load_dotenv()
        
        if config_path is None:
            # Try default locations
            possible_paths = [
                "config.yaml",
                "config/config.yaml",
                ".config/ai-cli/config.yaml",
                Path.home() / ".config" / "ai-cli" / "config.yaml"
            ]
            for p in possible_paths:
                if Path(p).exists():
                    config_path = str(p)
                    break
        
        config = cls.load_from_file(config_path) if config_path else cls()
        
        # Override with environment variables
        if os.getenv("AI_MODEL_PROVIDER"):
            config.model.provider = os.getenv("AI_MODEL_PROVIDER")
        if os.getenv("AI_MODEL_NAME"):
            config.model.name = os.getenv("AI_MODEL_NAME")
        if os.getenv("AI_API_BASE"):
            config.model.api_base = os.getenv("AI_API_BASE")
        if os.getenv("AI_SECURITY_MODE"):
            config.security.mode = os.getenv("AI_SECURITY_MODE")
        if os.getenv("AI_ALLOWED_ROOT"):
            config.security.allowed_root = os.getenv("AI_ALLOWED_ROOT")
        
        return config
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from environment"""
        if self.model.api_key_env:
            return os.getenv(self.model.api_key_env)
        return None

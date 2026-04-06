"""
AI Terminal Assistant - Main Package
"""
from .models import ActionType, Action, AIResponse, SecurityMode, OperationResult, AuditLogEntry
from .config import Config, ModelConfig, SecurityConfig, UIConfig, LoggingConfig
from .security import SecurityEngine
from .fs_executor import FileSystemExecutor
from .ai_adapter import BaseAIAdapter, OllamaAdapter, OpenAIAdapter, AnthropicAdapter, create_adapter
from .router import Router

__version__ = "0.1.0"
__all__ = [
    # Models
    'ActionType',
    'Action',
    'AIResponse',
    'SecurityMode',
    'OperationResult',
    'AuditLogEntry',
    
    # Config
    'Config',
    'ModelConfig',
    'SecurityConfig',
    'UIConfig',
    'LoggingConfig',
    
    # Core components
    'SecurityEngine',
    'FileSystemExecutor',
    'BaseAIAdapter',
    'OllamaAdapter',
    'OpenAIAdapter',
    'AnthropicAdapter',
    'create_adapter',
    'Router',
]

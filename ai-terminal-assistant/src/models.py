"""
AI Terminal Assistant - Core Models and Schemas
Defines Pydantic models for structured AI responses and validation
"""
from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
import re


class ActionType(str, Enum):
    """Supported file system operations"""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    APPEND_FILE = "append_file"
    RENAME_FILE = "rename_file"
    DELETE_FILE = "delete_file"
    LIST_DIR = "list_dir"


class Action(BaseModel):
    """Represents a single file system action proposed by the AI"""
    type: ActionType = Field(..., description="Type of operation to perform")
    path: str = Field(..., description="File or directory path (relative to workspace root)")
    content: Optional[str] = Field(None, description="Content for write/append operations")
    reason: Optional[str] = Field(None, description="Explanation of why this action is needed")
    new_path: Optional[str] = Field(None, description="Destination path for rename/move operations")
    max_depth: Optional[int] = Field(1, description="Maximum directory depth for list operations")
    
    @field_validator('path')
    @classmethod
    def validate_path_no_traversal(cls, v: str) -> str:
        """Prevent path traversal attacks"""
        if '..' in v:
            raise ValueError("Path traversal (..) is not allowed")
        if v.startswith('/'):
            raise ValueError("Absolute paths are not allowed, use relative paths only")
        return v
    
    @field_validator('new_path')
    @classmethod
    def validate_new_path_no_traversal(cls, v: Optional[str]) -> Optional[str]:
        """Prevent path traversal in destination path"""
        if v is None:
            return v
        if '..' in v:
            raise ValueError("Path traversal (..) is not allowed in destination")
        if v.startswith('/'):
            raise ValueError("Absolute paths are not allowed, use relative paths only")
        return v


class AIResponse(BaseModel):
    """Structured response from the AI model"""
    thought: str = Field(..., description="Brief explanation of the AI's reasoning and intentions")
    actions: List[Action] = Field(default_factory=list, description="List of proposed actions")
    response: Optional[str] = Field(None, description="Direct conversational response to the user (when no actions are needed or in addition to actions)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "thought": "I need to create a utility function and update the config",
                "actions": [
                    {
                        "type": "write_file",
                        "path": "src/utils.py",
                        "content": "def helper():\n    pass\n",
                        "reason": "Create new utility module"
                    },
                    {
                        "type": "read_file",
                        "path": "config.yaml"
                    }
                ]
            }
        }


class SecurityMode(str, Enum):
    """Security operation modes"""
    DRY_RUN = "dry_run"  # Show what would happen without executing
    INTERACTIVE = "interactive"  # Require confirmation for each action
    SCOPED_AUTO = "scoped_auto"  # Auto-execute within approved scope


class OperationResult(BaseModel):
    """Result of a file system operation"""
    success: bool
    action_type: ActionType
    path: str
    message: str
    content: Optional[str] = None  # For read operations
    backup_path: Optional[str] = None  # Path to backup if file was modified
    error: Optional[str] = None


class AuditLogEntry(BaseModel):
    """Entry for audit logging"""
    timestamp: str
    session_id: str
    prompt_hash: str
    action_type: Optional[ActionType]
    path: Optional[str]
    status: Literal["pending", "approved", "denied", "executed", "failed"]
    message: str
    metadata: dict = Field(default_factory=dict)

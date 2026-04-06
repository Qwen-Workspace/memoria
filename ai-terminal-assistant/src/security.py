"""
Security Engine for AI Terminal Assistant
Validates paths, actions, and enforces security policies
"""
import os
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
import hashlib

try:
    from .models import Action, ActionType, SecurityMode, OperationResult
    from .config import SecurityConfig
except ImportError:
    from models import Action, ActionType, SecurityMode, OperationResult
    from config import SecurityConfig


class SecurityEngine:
    """Validates and enforces security policies for file operations"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.allowed_root = Path(config.allowed_root).resolve()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def resolve_path(self, relative_path: str) -> Path:
        """Resolve relative path to absolute, preventing path traversal"""
        # Remove leading slashes and normalize
        clean_path = relative_path.lstrip('/')
        
        # Construct full path
        full_path = (self.allowed_root / clean_path).resolve()
        
        # Verify the resolved path is within allowed root
        try:
            full_path.relative_to(self.allowed_root)
        except ValueError:
            raise ValueError(f"Path traversal detected: {relative_path}")
        
        return full_path
    
    def validate_action(self, action: Action) -> Tuple[bool, str]:
        """
        Validate a single action against security policies
        Returns (is_valid, error_message)
        """
        try:
            # Check for path traversal in base path
            resolved_path = self.resolve_path(action.path)
            
            # Check if path is blocked
            path_parts = resolved_path.relative_to(self.allowed_root).parts
            for part in path_parts:
                if part in self.config.blocked_paths:
                    return False, f"Access to '{part}' directories is blocked"
            
            # Check file extension if allowlist is configured
            if self.config.allowed_extensions:
                ext = resolved_path.suffix.lower()
                if ext and ext not in self.config.allowed_extensions:
                    return False, f"File extension '{ext}' is not allowed"
            
            # Validate new_path for rename operations
            if action.new_path:
                resolved_new_path = self.resolve_path(action.new_path)
                try:
                    resolved_new_path.relative_to(self.allowed_root)
                except ValueError:
                    return False, f"Destination path traversal detected: {action.new_path}"
            
            # Check content size for write operations
            if action.content and action.type in [ActionType.WRITE_FILE, ActionType.APPEND_FILE]:
                content_size_mb = len(action.content.encode('utf-8')) / (1024 * 1024)
                if content_size_mb > self.config.max_file_size_mb:
                    return False, f"Content exceeds maximum size limit ({self.config.max_file_size_mb}MB)"
            
            # Check if file exists for certain operations
            if action.type == ActionType.READ_FILE and not resolved_path.exists():
                return False, f"File does not exist: {action.path}"
            
            if action.type == ActionType.DELETE_FILE and not resolved_path.exists():
                return False, f"Cannot delete non-existent file: {action.path}"
            
            if action.type == ActionType.RENAME_FILE and not resolved_path.exists():
                return False, f"Cannot rename non-existent file: {action.path}"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    def check_mode_permission(self, action: Action) -> bool:
        """Check if action is allowed in current security mode"""
        mode = SecurityMode(self.config.mode)
        
        if mode == SecurityMode.DRY_RUN:
            return True  # All actions allowed in dry-run (just won't execute)
        
        if mode == SecurityMode.INTERACTIVE:
            return True  # All actions allowed but require confirmation
        
        if mode == SecurityMode.SCOPED_AUTO:
            # In scoped auto mode, only read operations are automatic
            return action.type == ActionType.READ_FILE
        
        return False
    
    def requires_confirmation(self, action: Action) -> bool:
        """Determine if action requires user confirmation"""
        mode = SecurityMode(self.config.mode)
        
        if mode == SecurityMode.DRY_RUN:
            return False
        
        if mode == SecurityMode.INTERACTIVE:
            return True
        
        if mode == SecurityMode.SCOPED_AUTO:
            # Non-read operations require confirmation
            return action.type != ActionType.READ_FILE
        
        return True
    
    def hash_content(self, content: str) -> str:
        """Generate hash of content for audit trail"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def generate_backup_path(self, file_path: Path) -> Path:
        """Generate backup file path with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.bak.{timestamp}"
        return file_path.parent / backup_name

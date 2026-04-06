"""
File System Executor for AI Terminal Assistant
Safe wrapper for file operations with backup and audit support
"""
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

try:
    from .models import Action, ActionType, OperationResult
    from .security import SecurityEngine
except ImportError:
    from models import Action, ActionType, OperationResult
    from security import SecurityEngine


class FileSystemExecutor:
    """Executes file system operations with safety measures"""
    
    def __init__(self, security_engine: SecurityEngine):
        self.security = security_engine
    
    def execute(self, action: Action) -> OperationResult:
        """Execute a single action and return result"""
        try:
            # Validate action first
            is_valid, error_msg = self.security.validate_action(action)
            if not is_valid:
                return OperationResult(
                    success=False,
                    action_type=action.type,
                    path=action.path,
                    message="Validation failed",
                    error=error_msg
                )
            
            # Resolve path
            resolved_path = self.security.resolve_path(action.path)
            
            # Execute based on action type
            if action.type == ActionType.READ_FILE:
                return self._read_file(resolved_path, action.path)
            elif action.type == ActionType.WRITE_FILE:
                return self._write_file(resolved_path, action.content or "", action.path)
            elif action.type == ActionType.APPEND_FILE:
                return self._append_file(resolved_path, action.content or "", action.path)
            elif action.type == ActionType.DELETE_FILE:
                return self._delete_file(resolved_path, action.path)
            elif action.type == ActionType.RENAME_FILE:
                return self._rename_file(resolved_path, action.new_path, action.path)
            elif action.type == ActionType.LIST_DIR:
                return self._list_dir(resolved_path, action.path, action.max_depth or 1)
            else:
                return OperationResult(
                    success=False,
                    action_type=action.type,
                    path=action.path,
                    message="Unknown action type",
                    error=f"Unsupported action: {action.type}"
                )
                
        except Exception as e:
            return OperationResult(
                success=False,
                action_type=action.type,
                path=action.path,
                message="Execution failed",
                error=str(e)
            )
    
    def _read_file(self, path: Path, relative_path: str) -> OperationResult:
        """Read file content"""
        try:
            # Check file size
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.security.config.max_file_size_mb:
                return OperationResult(
                    success=False,
                    action_type=ActionType.READ_FILE,
                    path=relative_path,
                    message="File too large",
                    error=f"File exceeds maximum size limit ({self.security.config.max_file_size_mb}MB)"
                )
            
            # Try different encodings
            content = None
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    content = path.read_text(encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                return OperationResult(
                    success=False,
                    action_type=ActionType.READ_FILE,
                    path=relative_path,
                    message="Failed to decode file",
                    error="Unable to decode file with supported encodings"
                )
            
            return OperationResult(
                success=True,
                action_type=ActionType.READ_FILE,
                path=relative_path,
                message=f"Successfully read file ({len(content)} bytes)",
                content=content
            )
        except Exception as e:
            return OperationResult(
                success=False,
                action_type=ActionType.READ_FILE,
                path=relative_path,
                message="Failed to read file",
                error=str(e)
            )
    
    def _write_file(self, path: Path, content: str, relative_path: str) -> OperationResult:
        """Write file with automatic backup if it exists"""
        backup_path = None
        
        try:
            # Create backup if file exists
            if path.exists():
                backup_path = self.security.generate_backup_path(path)
                shutil.copy2(path, backup_path)
            
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            path.write_text(content, encoding='utf-8')
            
            return OperationResult(
                success=True,
                action_type=ActionType.WRITE_FILE,
                path=relative_path,
                message=f"Successfully wrote file ({len(content)} bytes)",
                backup_path=str(backup_path) if backup_path else None
            )
        except Exception as e:
            # Attempt rollback if backup exists
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, path)
                except:
                    pass  # Best effort rollback
            
            return OperationResult(
                success=False,
                action_type=ActionType.WRITE_FILE,
                path=relative_path,
                message="Failed to write file",
                error=str(e),
                backup_path=str(backup_path) if backup_path else None
            )
    
    def _append_file(self, path: Path, content: str, relative_path: str) -> OperationResult:
        """Append content to file"""
        try:
            # Create backup if file exists
            backup_path = None
            if path.exists():
                backup_path = self.security.generate_backup_path(path)
                shutil.copy2(path, backup_path)
            
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Append content
            with open(path, 'a', encoding='utf-8') as f:
                f.write(content)
            
            return OperationResult(
                success=True,
                action_type=ActionType.APPEND_FILE,
                path=relative_path,
                message=f"Successfully appended to file ({len(content)} bytes)",
                backup_path=str(backup_path) if backup_path else None
            )
        except Exception as e:
            return OperationResult(
                success=False,
                action_type=ActionType.APPEND_FILE,
                path=relative_path,
                message="Failed to append to file",
                error=str(e)
            )
    
    def _delete_file(self, path: Path, relative_path: str) -> OperationResult:
        """Delete file (permanent deletion, no backup)"""
        try:
            # Delete file permanently
            path.unlink()
            
            return OperationResult(
                success=True,
                action_type=ActionType.DELETE_FILE,
                path=relative_path,
                message="Successfully deleted file"
            )
        except Exception as e:
            return OperationResult(
                success=False,
                action_type=ActionType.DELETE_FILE,
                path=relative_path,
                message="Failed to delete file",
                error=str(e)
            )
    
    def _rename_file(self, path: Path, new_path_str: str, relative_path: str) -> OperationResult:
        """Rename/move file"""
        try:
            resolved_new_path = self.security.resolve_path(new_path_str)
            
            # Ensure parent directory exists
            resolved_new_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Rename file
            shutil.move(str(path), str(resolved_new_path))
            
            return OperationResult(
                success=True,
                action_type=ActionType.RENAME_FILE,
                path=relative_path,
                message=f"Successfully renamed to {new_path_str}"
            )
        except Exception as e:
            return OperationResult(
                success=False,
                action_type=ActionType.RENAME_FILE,
                path=relative_path,
                message="Failed to rename file",
                error=str(e)
            )
    
    def _list_dir(self, path: Path, relative_path: str, max_depth: int) -> OperationResult:
        """List directory contents"""
        try:
            if not path.is_dir():
                return OperationResult(
                    success=False,
                    action_type=ActionType.LIST_DIR,
                    path=relative_path,
                    message="Not a directory",
                    error=f"{relative_path} is not a directory"
                )
            
            entries = []
            self._scan_directory(path, entries, 0, max_depth)
            
            content = "\n".join(entries)
            
            return OperationResult(
                success=True,
                action_type=ActionType.LIST_DIR,
                path=relative_path,
                message=f"Listed {len(entries)} entries",
                content=content
            )
        except Exception as e:
            return OperationResult(
                success=False,
                action_type=ActionType.LIST_DIR,
                path=relative_path,
                message="Failed to list directory",
                error=str(e)
            )
    
    def _scan_directory(self, path: Path, entries: List[str], current_depth: int, max_depth: int):
        """Recursively scan directory"""
        if current_depth > max_depth:
            return
        
        try:
            for item in sorted(path.iterdir()):
                indent = "  " * current_depth
                if item.is_dir():
                    entries.append(f"{indent}[DIR] {item.name}/")
                    self._scan_directory(item, entries, current_depth + 1, max_depth)
                else:
                    size = item.stat().st_size
                    entries.append(f"{indent}[FILE] {item.name} ({size} bytes)")
        except PermissionError:
            entries.append("  " * current_depth + "[ERROR] Permission denied")

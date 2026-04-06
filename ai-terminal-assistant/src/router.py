"""
Router and Context Manager for AI Terminal Assistant
Orchestrates the flow between components and manages conversation context
"""
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

try:
    from .models import AIResponse, Action, AuditLogEntry, ActionType
    from .config import Config
    from .security import SecurityEngine
    from .fs_executor import FileSystemExecutor
    from .ai_adapter import BaseAIAdapter, create_adapter
except ImportError:
    from models import AIResponse, Action, AuditLogEntry, ActionType
    from config import Config
    from security import SecurityEngine
    from fs_executor import FileSystemExecutor
    from ai_adapter import BaseAIAdapter, create_adapter


SYSTEM_PROMPT = """You are an AI assistant with controlled access to the file system. 
You must respond with structured JSON containing your thought process and proposed actions.

IMPORTANT RULES:
1. All file paths must be relative to the workspace root (no absolute paths)
2. Never use path traversal (..) in your paths
3. Explain your reasoning in the "thought" field
4. Propose actions as a list with type, path, and content (for write operations)
5. Be concise but clear in your explanations

Available action types:
- read_file: Read content of a file
- write_file: Create or overwrite a file (requires content field)
- append_file: Append content to existing file
- rename_file: Rename/move a file (requires new_path field)
- delete_file: Delete a file (will create backup)
- list_dir: List directory contents (optional max_depth field)

Example response format:
{
  "thought": "I need to create a utility function and update the config",
  "actions": [
    {
      "type": "write_file",
      "path": "src/utils.py",
      "content": "def helper():\\n    pass\\n",
      "reason": "Create new utility module"
    },
    {
      "type": "read_file",
      "path": "config.yaml"
    }
  ]
}

Always respond with valid JSON only. Do not include markdown formatting or explanations outside the JSON structure."""


class Router:
    """Orchestrates communication between components"""
    
    def __init__(self, config: Config):
        self.config = config
        self.security_engine = SecurityEngine(config.security)
        self.fs_executor = FileSystemExecutor(self.security_engine)
        self.ai_adapter = self._create_ai_adapter()
        self.conversation_history: List[Dict[str, str]] = []
        self.session_id = self.security_engine.session_id
        self.audit_log_path = Path(config.logging.audit_path)
        
        # Ensure audit log directory exists
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _create_ai_adapter(self) -> BaseAIAdapter:
        """Create appropriate AI adapter based on config"""
        api_key = self.config.get_api_key()
        
        return create_adapter(
            provider=self.config.model.provider,
            api_key=api_key,
            api_base=self.config.model.api_base,
            model_name=self.config.model.name,
            temperature=self.config.model.temperature,
            max_tokens=self.config.model.max_tokens
        )
    
    def _hash_prompt(self, prompt: str) -> str:
        """Generate hash of prompt for audit trail"""
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    
    def _log_audit(self, entry: AuditLogEntry):
        """Write audit log entry"""
        with open(self.audit_log_path, 'a', encoding='utf-8') as f:
            f.write(entry.model_dump_json() + '\n')
    
    async def process_prompt(self, prompt: str) -> Dict:
        """
        Process user prompt through the complete pipeline
        Returns dict with results and status
        """
        prompt_hash = self._hash_prompt(prompt)
        timestamp = datetime.now().isoformat()
        
        # Log initial prompt
        self._log_audit(AuditLogEntry(
            timestamp=timestamp,
            session_id=self.session_id,
            prompt_hash=prompt_hash,
            action_type=None,
            path=None,
            status="pending",
            message="User prompt received",
            metadata={"prompt_length": len(prompt)}
        ))
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": prompt})
        
        try:
            # Get AI response
            ai_response = await self.ai_adapter.chat(
                messages=self.conversation_history[-10:],  # Last 10 messages for context
                system_prompt=SYSTEM_PROMPT
            )
            
            # Add AI response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": json.dumps(ai_response.model_dump())
            })
            
            # Validate and execute actions
            results = []
            for action in ai_response.actions:
                # Validate action
                is_valid, error_msg = self.security_engine.validate_action(action)
                
                if not is_valid:
                    result = {
                        "action": action.model_dump(),
                        "status": "denied",
                        "message": error_msg
                    }
                    results.append(result)
                    
                    self._log_audit(AuditLogEntry(
                        timestamp=datetime.now().isoformat(),
                        session_id=self.session_id,
                        prompt_hash=prompt_hash,
                        action_type=action.type,
                        path=action.path,
                        status="denied",
                        message=error_msg,
                        metadata=action.model_dump()
                    ))
                    continue
                
                # Check if confirmation is required
                if self.security_engine.requires_confirmation(action):
                    result = {
                        "action": action.model_dump(),
                        "status": "pending_confirmation",
                        "message": "Requires user confirmation",
                        "reason": action.reason
                    }
                    results.append(result)
                else:
                    # Execute action (dry-run or auto-approved)
                    execution_result = self.fs_executor.execute(action)
                    
                    result = {
                        "action": action.model_dump(),
                        "status": "executed" if execution_result.success else "failed",
                        "message": execution_result.message,
                        "content": execution_result.content,
                        "backup_path": execution_result.backup_path,
                        "error": execution_result.error
                    }
                    results.append(result)
                    
                    self._log_audit(AuditLogEntry(
                        timestamp=datetime.now().isoformat(),
                        session_id=self.session_id,
                        prompt_hash=prompt_hash,
                        action_type=action.type,
                        path=action.path,
                        status="executed" if execution_result.success else "failed",
                        message=execution_result.message,
                        metadata={
                            **action.model_dump(),
                            "backup_path": execution_result.backup_path
                        }
                    ))
            
            # Log successful AI response
            self._log_audit(AuditLogEntry(
                timestamp=datetime.now().isoformat(),
                session_id=self.session_id,
                prompt_hash=prompt_hash,
                action_type=None,
                path=None,
                status="approved",
                message="AI response processed",
                metadata={
                    "thought": ai_response.thought,
                    "action_count": len(ai_response.actions)
                }
            ))
            
            return {
                "success": True,
                "thought": ai_response.thought,
                "actions": results,
                "mode": self.config.security.mode
            }
            
        except Exception as e:
            error_msg = str(e)
            
            self._log_audit(AuditLogEntry(
                timestamp=datetime.now().isoformat(),
                session_id=self.session_id,
                prompt_hash=prompt_hash,
                action_type=None,
                path=None,
                status="failed",
                message=f"Error processing prompt: {error_msg}",
                metadata={"error_type": type(e).__name__}
            ))
            
            return {
                "success": False,
                "error": error_msg,
                "mode": self.config.security.mode
            }
    
    def confirm_action(self, action_data: Dict, confirmed: bool) -> Dict:
        """Process user confirmation for pending action"""
        if not confirmed:
            return {
                "status": "denied",
                "message": "Action denied by user"
            }
        
        # Execute the confirmed action
        action = Action(**action_data)
        execution_result = self.fs_executor.execute(action)
        
        self._log_audit(AuditLogEntry(
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            prompt_hash="",
            action_type=action.type,
            path=action.path,
            status="executed" if execution_result.success else "failed",
            message=execution_result.message,
            metadata={
                **action.model_dump(),
                "backup_path": execution_result.backup_path
            }
        ))
        
        return {
            "status": "executed" if execution_result.success else "failed",
            "message": execution_result.message,
            "content": execution_result.content,
            "backup_path": execution_result.backup_path,
            "error": execution_result.error
        }
    
    def get_context_summary(self) -> Dict:
        """Get summary of current conversation context"""
        return {
            "session_id": self.session_id,
            "message_count": len(self.conversation_history),
            "allowed_root": str(self.security_engine.allowed_root),
            "security_mode": self.config.security.mode,
            "max_file_size_mb": self.config.security.max_file_size_mb
        }
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self._log_audit(AuditLogEntry(
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            prompt_hash="",
            action_type=None,
            path=None,
            status="approved",
            message="Conversation history cleared",
            metadata={}
        ))

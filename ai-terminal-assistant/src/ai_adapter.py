"""
AI Adapter for AI Terminal Assistant
Abstracts communication with different AI model providers
"""
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx

try:
    from .models import AIResponse
except ImportError:
    from models import AIResponse


class BaseAIAdapter(ABC):
    """Base class for AI model adapters"""
    
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.api_base = api_base
        self.kwargs = kwargs
    
    @abstractmethod
    async def chat(self, messages: list[Dict[str, str]], system_prompt: str) -> AIResponse:
        """Send chat request and get structured response"""
        pass
    
    def parse_response(self, response_text: str) -> AIResponse:
        """Parse AI response into structured format"""
        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
                return AIResponse(**data)
            else:
                # Fallback: create a simple response
                return AIResponse(
                    thought="Could not parse structured response",
                    actions=[]
                )
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse AI response: {e}")


class OllamaAdapter(BaseAIAdapter):
    """Adapter for Ollama local models"""
    
    async def chat(self, messages: list[Dict[str, str]], system_prompt: str) -> AIResponse:
        """Send chat request to Ollama"""
        base_url = self.api_base or "http://localhost:11434"
        
        # Try the /api/chat endpoint first (newer Ollama versions)
        url = f"{base_url}/api/chat"
        
        payload = {
            "model": self.kwargs.get("model_name", "qwen2.5:1.5b"),
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages
            ],
            "stream": False,
            "options": {
                "temperature": self.kwargs.get("temperature", 0.7),
            }
        }
        
        if self.kwargs.get("max_tokens"):
            payload["options"]["num_predict"] = self.kwargs["max_tokens"]
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, json=payload)
                
                # If /api/chat returns 404, try /api/generate (older format)
                if response.status_code == 404:
                    url = f"{base_url}/api/generate"
                    # Convert to generate format (single prompt string)
                    prompt_text = f"{system_prompt}\n\n"
                    for msg in messages:
                        role = msg["role"].upper()
                        content = msg["content"]
                        prompt_text += f"{role}: {content}\n"
                    prompt_text += "ASSISTANT:"
                    
                    payload = {
                        "model": self.kwargs.get("model_name", "qwen2.5:1.5b"),
                        "prompt": prompt_text,
                        "stream": False,
                        "options": {
                            "temperature": self.kwargs.get("temperature", 0.7),
                        }
                    }
                    if self.kwargs.get("max_tokens"):
                        payload["options"]["num_predict"] = self.kwargs["max_tokens"]
                    
                    response = await client.post(url, json=payload)
                
                response.raise_for_status()
                data = response.json()
                
                # Handle both response formats
                if "message" in data:
                    assistant_message = data.get("message", {}).get("content", "")
                elif "response" in data:
                    assistant_message = data.get("response", "")
                else:
                    assistant_message = ""
                
                return self.parse_response(assistant_message)
                
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Ollama API error ({e.response.status_code}): {e.response.text}")
            except httpx.ConnectError as e:
                raise RuntimeError(f"Cannot connect to Ollama at {base_url}. Is Ollama running? (Try: ollama serve)")


class OpenAIAdapter(BaseAIAdapter):
    """Adapter for OpenAI and compatible APIs"""
    
    async def chat(self, messages: list[Dict[str, str]], system_prompt: str) -> AIResponse:
        """Send chat request to OpenAI"""
        url = f"{self.api_base or 'https://api.openai.com/v1'}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.kwargs.get("model_name", "gpt-3.5-turbo"),
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages
            ],
            "temperature": self.kwargs.get("temperature", 0.7),
        }
        
        if self.kwargs.get("max_tokens"):
            payload["max_tokens"] = self.kwargs["max_tokens"]
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            assistant_message = data["choices"][0]["message"]["content"]
            return self.parse_response(assistant_message)


class AnthropicAdapter(BaseAIAdapter):
    """Adapter for Anthropic Claude models"""
    
    async def chat(self, messages: list[Dict[str, str]], system_prompt: str) -> AIResponse:
        """Send chat request to Anthropic"""
        url = f"{self.api_base or 'https://api.anthropic.com/v1'}/messages"
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            anthropic_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        payload = {
            "model": self.kwargs.get("model_name", "claude-3-sonnet-20240229"),
            "max_tokens": self.kwargs.get("max_tokens", 4096),
            "system": system_prompt,
            "messages": anthropic_messages,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            assistant_message = data["content"][0]["text"]
            return self.parse_response(assistant_message)


def create_adapter(provider: str, **kwargs) -> BaseAIAdapter:
    """Factory function to create appropriate adapter"""
    adapters = {
        "ollama": OllamaAdapter,
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
    }
    
    adapter_class = adapters.get(provider.lower())
    if not adapter_class:
        raise ValueError(f"Unsupported provider: {provider}")
    
    return adapter_class(**kwargs)

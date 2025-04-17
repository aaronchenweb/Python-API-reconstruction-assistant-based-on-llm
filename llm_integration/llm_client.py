"""
用於與不同 LLM 提供商通信的 LLM API 客戶端。
支持 OpenAI、Anthropic 和 Gemini 提供商。
"""
import os
import json
import logging
import time
import httpx
from typing import Dict, Any, Optional, List, Union


class LLMClient:
    """
    用於與不同 LLM 提供商通信的 LLM API 客戶端。
    支持 OpenAI、Anthropic 和 Gemini 提供商。
    """
    
    def __init__(self, api_key: str = "", model: str = "", provider: str = 'openai'):
        """
        初始化 LLM 客戶端
        
        Args:
            api_key: API 密鑰
            model: 模型名稱
            provider: 提供商 ('gemini','openai', 'anthropic' 等)
        """
        self.api_key = api_key
        self.model = model
        self.provider = provider.lower()
        
        # 速率限制變量
        self.last_request_time = 0
        self.min_request_interval = 4.0  # Minimum 4 seconds between API calls

        # 設置 API 端點
        if self.provider == 'gemini':
            self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
            if not model:
                self.model = "gemini-1.5-flash"
        elif self.provider == 'openai':
            self.api_url = "https://api.openai.com/v1/chat/completions"
            if not model:
                self.model = "gpt-4"
        elif self.provider == 'anthropic':
            self.api_url = "https://api.anthropic.com/v1/messages"
            if not model:
                self.model = "claude-3-opus-20240229"
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def is_available(self) -> bool:
        """
        檢查 LLM API 是否可用（有效的 API 密鑰）
        
        Returns:
            如果 API 密鑰已設置且有效則返回 True，否則返回 False
        """
        return bool(self.api_key)
    
    def _apply_rate_limit(self):
        """
        應用速率限制以防止 API 速率限制錯誤。
        確保 API 調用之間至少間隔 min_request_interval 秒。
        """
        current_time = time.time()
        elapsed_time = current_time - self.last_request_time
        
        # 如果自上次請求以來未經過足夠的時間，則等待
        if elapsed_time < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed_time
            logging.info(f"Rate limiting: Waiting {wait_time:.2f} seconds before next API call")
            time.sleep(wait_time)
        
        # 更新上次請求時間
        self.last_request_time = time.time()

    def get_completion(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        獲取 LLM 對提示的回應
        
        Args:
            prompt: 提示文本
            max_tokens: 回應的最大標記數
            
        Returns:
            LLM 生成的回應文本
        """
        # 檢查 API 密鑰是否存在
        if not self.api_key:
            # 返回模擬回應以避免 API 錯誤
            logging.warning("API key not set, returning mock response")
            return self._get_mock_response(prompt)
        
        # 在進行任何 API 調用之前應用速率限制
        self._apply_rate_limit()

        if self.provider == 'openai':
            return self._openai_completion(prompt, max_tokens)
        elif self.provider == 'anthropic':
            return self._anthropic_completion(prompt, max_tokens)
        elif self.provider == 'gemini':
            return self._gemini_completion(prompt, max_tokens)
        else:
            logging.error(f"Unimplemented provider: {self.provider}")
            return f"Error: No support implemented for {self.provider} provider"
    
    def get_structured_completion(self, prompt: str, max_tokens: int = 1000) -> Dict[str, Any]:
        """
        從 LLM 獲取結構化回應（JSON 格式）
        
        Args:
            prompt: 提示文本
            max_tokens: 回應的最大標記數
            
        Returns:
            包含結構化回應的字典
        """
        # 添加將回應格式化為 JSON 的指令
        json_prompt = f"{prompt}\n\nPlease format your response as valid JSON."
        
        # 獲取完成
        response = self.get_completion(json_prompt, max_tokens)
        
        # 嘗試從回應中解析 JSON
        try:
            # 如果 JSON 被代碼塊包裹，則提取 JSON 部分
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                response = json_match.group(1)
            
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果 JSON 解析失敗，則返回原始文本
            return {"text": response}
    
    def _openai_completion(self, prompt: str, max_tokens: int) -> str:
        """OpenAI API 調用"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()
                
                # 確保返回的內容不為 None
                content = response_data['choices'][0]['message']['content']
                return content if content is not None else ""
        
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            return f"API request failed: HTTP {e.response.status_code}. Please check your API key and settings."
        
        except Exception as e:
            logging.error(f"Error calling OpenAI API: {str(e)}")
            return f"Error calling API: {str(e)}. Please check your network connection and API settings."
    
    def _anthropic_completion(self, prompt: str, max_tokens: int) -> str:
        """Anthropic API 調用"""
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()
                
                # 確保返回的內容不為 None
                content = response_data['content'][0]['text']
                return content if content is not None else ""
        
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            return f"API request failed: HTTP {e.response.status_code}. Please check your API key and settings."
        
        except Exception as e:
            logging.error(f"Error calling Anthropic API: {str(e)}")
            return f"Error calling API: {str(e)}. Please check your network connection and API settings."
            
    def _gemini_completion(self, prompt: str, max_tokens: int) -> str:
        """Gemini API 調用"""
        headers = {
            "Content-Type": "application/json"
        }
        
        # Gemini API 需要將 API 密鑰作為 URL 參數
        api_url_with_key = f"{self.api_url}?key={self.api_key}"
        
        # Gemini API 請求格式
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(api_url_with_key, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()
                
                # 解析 Gemini 回應
                if 'candidates' in response_data and len(response_data['candidates']) > 0:
                    if 'content' in response_data['candidates'][0] and 'parts' in response_data['candidates'][0]['content']:
                        # 獲取文本回應
                        text_parts = [part.get('text', '') for part in response_data['candidates'][0]['content']['parts'] if 'text' in part]
                        return ''.join(text_parts) if text_parts else ""
                
                # 如果無法解析回應，則返回空字符串
                logging.error(f"Cannot parse Gemini API response: {response_data}")
                return ""
        
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            # 如果達到速率限制，記錄特定消息
            if e.response.status_code == 429:
                logging.warning("Rate limit exceeded (429 Too Many Requests). Consider increasing the min_request_interval.")
                
            return f"API request failed: HTTP {e.response.status_code}. Please check your API key and settings."
        
        except Exception as e:
            logging.error(f"Error calling Gemini API: {str(e)}")
            return f"Error calling API: {str(e)}. Please check your network connection and API settings."
    
    def _get_mock_response(self, prompt: str) -> str:
        """
        當沒有可用的 API 密鑰時返回模擬回應
        
        Args:
            prompt: 提示文本
            
        Returns:
            模擬分析回應
        """
        # 檢查提示是否包含 Python 代碼
        if "```python" in prompt:
            return """
## Code Analysis Result (Mock Response)

### Structure Evaluation
This code has a clear structure with class definitions and functions, but there are some areas for improvement:
1. Consider more modularized design
2. Some functions might be too complex and could be broken down into smaller functions

### Potential Issues
1. Use of global variables might make maintenance difficult
2. Some functions lack sufficient error handling
3. There are hardcoded values that could be moved to configuration files

### Design Pattern Suggestions
Consider applying these design patterns:
1. Factory Pattern - For object creation
2. Strategy Pattern - For different data processing strategies

### Code Style
Overall code style is good, but can be improved:
1. Add more complete docstrings
2. Ensure function names follow PEP 8 naming conventions

Note: This is a mock response, no actual LLM analysis was performed. Please set a valid API key for more accurate analysis.
"""
        else:
            return "Unable to analyze the provided content. This is a mock response because no API key was set."
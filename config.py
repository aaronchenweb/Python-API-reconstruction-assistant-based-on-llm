import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加載配置文件
    
    Args:
        config_path: 配置文件路徑，如果為None則使用默認值
        
    Returns:
        配置字典
    """
    default_config = {
        "llm_provider": "gemini",
        "llm_model": "gemini-1.5-flash",
        "llm_api_key": os.environ.get("LLM_API_KEY", ""),
        "max_tokens": 1000,
        "log_level": "INFO"
    }
    
    if not config_path or not os.path.exists(config_path):
        return default_config
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            user_config = json.load(file)
            # 合併默認配置和用戶配置
            config = {**default_config, **user_config}
            return config
    except Exception as e:
        print(f"警告: 讀取配置文件時出錯: {str(e)}，使用默認配置")
        return default_config
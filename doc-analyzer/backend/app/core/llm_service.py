"""
LLM 服务接口
预留大模型 API 接口
"""
import json
from typing import Dict, List, Optional
from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """LLM 提供商基类"""
    
    def __init__(self, api_key: str, api_base: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
    
    @abstractmethod
    def extract_keywords(self, text: str, top_n: int = 15) -> List[Dict[str, float]]:
        """提取关键词"""
        pass
    
    @abstractmethod
    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """生成摘要"""
        pass
    
    @abstractmethod
    def analyze_document(self, text: str) -> Dict[str, any]:
        """完整文档分析"""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT 接口"""
    
    def extract_keywords(self, text: str, top_n: int = 15) -> List[Dict[str, float]]:
        """使用 GPT 提取关键词"""
        # 预留实现
        # from openai import OpenAI
        # client = OpenAI(api_key=self.api_key, base_url=self.api_base)
        # ...
        return []
    
    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """使用 GPT 生成摘要"""
        # 预留实现
        return ""
    
    def analyze_document(self, text: str) -> Dict[str, any]:
        """完整文档分析"""
        # 预留实现
        return {
            "keywords": [],
            "summary": "",
            "method": "openai"
        }


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude 接口"""
    
    def extract_keywords(self, text: str, top_n: int = 15) -> List[Dict[str, float]]:
        """使用 Claude 提取关键词"""
        # 预留实现
        return []
    
    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """使用 Claude 生成摘要"""
        # 预留实现
        return ""
    
    def analyze_document(self, text: str) -> Dict[str, any]:
        """完整文档分析"""
        # 预留实现
        return {
            "keywords": [],
            "summary": "",
            "method": "claude"
        }


class WenxinProvider(BaseLLMProvider):
    """百度文心一言接口"""
    
    def extract_keywords(self, text: str, top_n: int = 15) -> List[Dict[str, float]]:
        """使用文心一言提取关键词"""
        # 预留实现
        return []
    
    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """使用文心一言生成摘要"""
        # 预留实现
        return ""
    
    def analyze_document(self, text: str) -> Dict[str, any]:
        """完整文档分析"""
        # 预留实现
        return {
            "keywords": [],
            "summary": "",
            "method": "wenxin"
        }


class LLMService:
    """LLM 服务管理"""
    
    PROVIDERS = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "wenxin": WenxinProvider,
    }
    
    @classmethod
    def get_provider(cls, provider_name: str, api_key: str, 
                     api_base: Optional[str] = None, 
                     model: Optional[str] = None) -> Optional[BaseLLMProvider]:
        """获取 LLM 提供商实例"""
        provider_class = cls.PROVIDERS.get(provider_name)
        if provider_class:
            return provider_class(api_key, api_base, model)
        return None
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """列出支持的提供商"""
        return list(cls.PROVIDERS.keys())


def analyze_with_llm(text: str, provider: str = "openai", 
                     api_key: Optional[str] = None) -> Dict[str, any]:
    """
    使用 LLM 分析文档
    
    Args:
        text: 文档文本
        provider: 提供商名称
        api_key: API Key
    
    Returns:
        {
            "keywords": [{"word": "...", "weight": 0.9}, ...],
            "summary": "...",
            "method": "llm"
        }
    """
    if not api_key:
        raise ValueError("API Key 不能为空")
    
    llm = LLMService.get_provider(provider, api_key)
    if not llm:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")
    
    return llm.analyze_document(text)

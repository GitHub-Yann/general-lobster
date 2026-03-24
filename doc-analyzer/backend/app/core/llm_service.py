"""
LLM 服务接口
支持在抽取结果基础上进行可控重写整合
"""
import json
import re
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

import requests


DEFAULT_SYSTEM_PROMPT = (
    "你是文档分析助手。你只能基于给定内容重写，不得编造事实。"
    "请输出严格 JSON："
    "{\"keywords\":[{\"word\":\"关键词\",\"weight\":0.0}],\"summary\":\"摘要\"}。"
    "关键词数量不超过15，摘要应是简介风格，语言简洁准确。"
)

DEFAULT_USER_TEMPLATE = (
    "请根据以下输入进行重写整合，保留关键术语并避免新增事实：\n"
    "{payload}"
)


class BaseLLMProvider(ABC):
    """LLM 提供商基类"""

    def __init__(self, api_key: str, api_base: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str, timeout: int = 60) -> str:
        """调用对话接口并返回文本"""
        raise NotImplementedError

    def refine_result(
        self,
        payload: Dict[str, Any],
        system_prompt: str,
        user_prompt_template: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """基于输入 payload 进行关键词+摘要整合"""
        prompt = (user_prompt_template or DEFAULT_USER_TEMPLATE).replace(
            "{payload}", json.dumps(payload, ensure_ascii=False)
        )
        raw_text = self.chat(system_prompt or DEFAULT_SYSTEM_PROMPT, prompt, timeout=timeout)
        parsed = _parse_llm_json(raw_text)
        return {
            "keywords": parsed.get("keywords", []),
            "summary": parsed.get("summary", ""),
            "raw_text": raw_text
        }

    def extract_keywords(self, text: str, top_n: int = 15) -> List[Dict[str, float]]:
        """兼容旧接口"""
        payload = {"text": text[:5000], "top_n": top_n}
        data = self.refine_result(payload, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_TEMPLATE)
        keywords = data.get("keywords", [])
        if isinstance(keywords, list):
            return keywords[:top_n]
        return []

    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """兼容旧接口"""
        payload = {"text": text[:8000], "max_length": max_length}
        data = self.refine_result(payload, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_TEMPLATE)
        summary = str(data.get("summary", ""))
        return summary[:max_length]

    def analyze_document(self, text: str) -> Dict[str, Any]:
        """兼容旧接口"""
        payload = {"text": text[:8000]}
        data = self.refine_result(payload, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_TEMPLATE)
        return {
            "keywords": data.get("keywords", []),
            "summary": data.get("summary", ""),
            "method": "llm"
        }


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI 兼容接口（多数厂商支持）"""

    def chat(self, system_prompt: str, user_prompt: str, timeout: int = 60) -> str:
        if not self.api_base:
            raise ValueError("api_base 不能为空（OpenAI兼容接口需要）")

        url = self.api_base.rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude 原生接口"""

    def chat(self, system_prompt: str, user_prompt: str, timeout: int = 60) -> str:
        base = self.api_base or "https://api.anthropic.com"
        url = base.rstrip("/") + "/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model or "claude-3-5-sonnet-20241022",
            "max_tokens": 1200,
            "temperature": 0.2,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", [])
        if isinstance(content, list) and content:
            text_part = content[0]
            if isinstance(text_part, dict):
                return str(text_part.get("text", ""))
        return ""


class WenxinProvider(OpenAICompatibleProvider):
    """文心一言（使用兼容接口）"""
    pass


class LLMService:
    """LLM 服务管理"""

    PROVIDERS = {
        "openai": OpenAICompatibleProvider,
        "claude": ClaudeProvider,
        "wenxin": WenxinProvider,
    }

    @classmethod
    def get_provider(
        cls,
        provider_name: str,
        api_key: str,
        api_base: Optional[str] = None,
        model: Optional[str] = None
    ) -> Optional[BaseLLMProvider]:
        provider_class = cls.PROVIDERS.get((provider_name or "").lower())
        if provider_class:
            return provider_class(api_key, api_base, model)
        return None

    @classmethod
    def list_providers(cls) -> List[str]:
        return list(cls.PROVIDERS.keys())

    @classmethod
    def refine_keywords_and_summary(
        cls,
        provider_name: str,
        api_key: str,
        api_base: Optional[str],
        model: Optional[str],
        payload: Dict[str, Any],
        system_prompt: str,
        user_prompt_template: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        provider = cls.get_provider(provider_name, api_key, api_base, model)
        if not provider:
            raise ValueError(f"不支持的 LLM 提供商: {provider_name}")
        return provider.refine_result(payload, system_prompt, user_prompt_template, timeout=timeout)


def analyze_with_llm(text: str, provider: str = "openai", api_key: Optional[str] = None) -> Dict[str, Any]:
    """兼容旧调用"""
    if not api_key:
        raise ValueError("API Key 不能为空")
    llm = LLMService.get_provider(provider, api_key)
    if not llm:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")
    return llm.analyze_document(text)


def _parse_llm_json(raw_text: str) -> Dict[str, Any]:
    """解析 LLM 输出，支持 code fence 与文本包裹 JSON"""
    if not raw_text:
        return {"keywords": [], "summary": ""}

    text = raw_text.strip()
    # 优先解析 ```json ... ```
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        # 兜底提取第一个 JSON 对象
        obj_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if obj_match:
            text = obj_match.group(1).strip()

    try:
        data = json.loads(text)
    except Exception:
        return {"keywords": [], "summary": ""}

    keywords = data.get("keywords", [])
    summary = data.get("summary", "")
    if not isinstance(keywords, list):
        keywords = []
    if not isinstance(summary, str):
        summary = str(summary)

    normalized_keywords = []
    for item in keywords[:15]:
        if isinstance(item, dict):
            word = str(item.get("word", "")).strip()
            if not word:
                continue
            weight = item.get("weight", 0.5)
            try:
                weight = float(weight)
            except Exception:
                weight = 0.5
            weight = max(0.0, min(1.0, weight))
            normalized_keywords.append({"word": word, "weight": round(weight, 4)})
        elif isinstance(item, str):
            w = item.strip()
            if w:
                normalized_keywords.append({"word": w, "weight": 0.5})

    return {
        "keywords": normalized_keywords,
        "summary": summary.strip()
    }

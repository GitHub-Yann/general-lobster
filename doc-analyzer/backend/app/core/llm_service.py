"""
LLM 服务接口（统一 OpenAI 兼容调用）
"""
import json
import re
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import logging

import requests

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "你是文档分析助手。你只能基于给定内容重写，不得编造事实。"
    "输出严格JSON：{\"keywords\":[{\"word\":\"关键词\",\"weight\":0.00}],\"summary\":\"摘要\"}。"
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

        # 按需求：调用地址使用配置值原样，不做拼接
        url = self.api_base.strip()

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
        logger.info(f"[LLM] POST {url} -> HTTP {resp.status_code}")
        if not resp.ok:
            logger.warning(f"[LLM] response body (first 500 chars): {resp.text[:500]}")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class LLMService:
    """LLM 服务管理（统一走 OpenAICompatibleProvider）"""

    @classmethod
    def get_provider(
        cls,
        provider_name: str,
        api_key: str,
        api_base: Optional[str] = None,
        model: Optional[str] = None
    ) -> Optional[BaseLLMProvider]:
        # 按需求：不根据 provider_name 分发，统一使用 OpenAI 兼容调用
        return OpenAICompatibleProvider(api_key, api_base, model)

    @classmethod
    def list_providers(cls) -> List[str]:
        # 仅作为展示用途
        return ["openai_compatible"]

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

"""
LLM 配置 API 路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.llm_config import LLMConfig
from app.core.llm_service import LLMService

router = APIRouter()


@router.get("/providers")
async def list_providers():
    """列出支持的 LLM 提供商"""
    return {
        "providers": LLMService.list_providers()
    }


@router.get("")
async def list_llm_configs(db: Session = Depends(get_db)):
    """获取 LLM 配置列表"""
    configs = db.query(LLMConfig).all()
    return {
        "items": [config.to_dict() for config in configs]
    }


@router.post("")
async def create_llm_config(
    provider: str,
    name: str,
    api_key: str,
    api_base: Optional[str] = None,
    model: Optional[str] = None,
    enabled: bool = False,
    db: Session = Depends(get_db)
):
    """创建 LLM 配置"""
    # 验证提供商
    if provider not in LLMService.list_providers():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的提供商: {provider}"
        )
    
    # 检查名称是否已存在
    existing = db.query(LLMConfig).filter(LLMConfig.name == name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置名称已存在: {name}"
        )
    
    config = LLMConfig(
        provider=provider,
        name=name,
        api_key=api_key,
        api_base=api_base,
        model=model,
        enabled=enabled
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return {
        "id": config.id,
        "message": "配置创建成功"
    }


@router.put("/{config_id}")
async def update_llm_config(
    config_id: int,
    provider: Optional[str] = None,
    name: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    model: Optional[str] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """更新 LLM 配置"""
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    if provider:
        config.provider = provider
    if name:
        config.name = name
    if api_key:
        config.api_key = api_key
    if api_base is not None:
        config.api_base = api_base
    if model:
        config.model = model
    if enabled is not None:
        config.enabled = enabled
    
    db.commit()
    db.refresh(config)
    
    return {
        "id": config.id,
        "message": "配置更新成功"
    }


@router.delete("/{config_id}")
async def delete_llm_config(config_id: int, db: Session = Depends(get_db)):
    """删除 LLM 配置"""
    config = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    db.delete(config)
    db.commit()
    
    return {
        "message": "配置删除成功"
    }

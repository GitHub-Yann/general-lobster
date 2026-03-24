"""
LLM 配置 API 路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.llm_config import LLMConfig
from app.models.llm_prompt_template import LLMPromptTemplate
from app.core.llm_service import LLMService

router = APIRouter()


@router.get("/providers")
async def list_providers():
    """列出支持的 LLM 提供商"""
    return {
        "providers": LLMService.list_providers()
    }


@router.get("")
async def list_llm_configs(enabled: Optional[bool] = None, db: Session = Depends(get_db)):
    """获取 LLM 配置列表"""
    query = db.query(LLMConfig)
    if enabled is not None:
        query = query.filter(LLMConfig.enabled == enabled)
    configs = query.order_by(LLMConfig.updated_at.desc()).all()
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


@router.get("/prompts")
async def list_prompt_templates(
    scene: Optional[str] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取 Prompt 模板列表"""
    query = db.query(LLMPromptTemplate)
    if scene:
        query = query.filter(LLMPromptTemplate.scene == scene)
    if enabled is not None:
        query = query.filter(LLMPromptTemplate.enabled == enabled)
    items = query.order_by(LLMPromptTemplate.updated_at.desc()).all()
    return {"items": [item.to_dict() for item in items]}


@router.post("/prompts")
async def create_prompt_template(
    name: str,
    scene: str = "doc_refine",
    version: str = "v1",
    system_prompt: str = "",
    user_prompt_template: str = "",
    enabled: bool = True,
    db: Session = Depends(get_db)
):
    """创建 Prompt 模板"""
    if not system_prompt.strip() or not user_prompt_template.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="system_prompt 和 user_prompt_template 不能为空"
        )

    existing = db.query(LLMPromptTemplate).filter(
        LLMPromptTemplate.name == name,
        LLMPromptTemplate.scene == scene,
        LLMPromptTemplate.version == version
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"模板已存在: {name}/{scene}/{version}"
        )

    item = LLMPromptTemplate(
        name=name,
        scene=scene,
        version=version,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        enabled=enabled
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "message": "模板创建成功"}


@router.put("/prompts/{template_id}")
async def update_prompt_template(
    template_id: int,
    name: Optional[str] = None,
    scene: Optional[str] = None,
    version: Optional[str] = None,
    system_prompt: Optional[str] = None,
    user_prompt_template: Optional[str] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """更新 Prompt 模板"""
    item = db.query(LLMPromptTemplate).filter(LLMPromptTemplate.id == template_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")

    if name:
        item.name = name
    if scene:
        item.scene = scene
    if version:
        item.version = version
    if system_prompt is not None:
        item.system_prompt = system_prompt
    if user_prompt_template is not None:
        item.user_prompt_template = user_prompt_template
    if enabled is not None:
        item.enabled = enabled

    db.commit()
    db.refresh(item)
    return {"id": item.id, "message": "模板更新成功"}


@router.delete("/prompts/{template_id}")
async def delete_prompt_template(template_id: int, db: Session = Depends(get_db)):
    """删除 Prompt 模板"""
    item = db.query(LLMPromptTemplate).filter(LLMPromptTemplate.id == template_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    db.delete(item)
    db.commit()
    return {"message": "模板删除成功"}

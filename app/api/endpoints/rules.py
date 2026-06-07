"""
筛选规则 CRUD API - 通过 Web 界面配置重点资产筛选规则
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rule import FilterRule
from app.schemas.schemas import FilterRuleCreate, FilterRuleUpdate, FilterRuleOut
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/rules", tags=["rules"])
logger = get_logger("api.rules")


@router.get("/", response_model=List[FilterRuleOut])
async def list_rules(db: Session = Depends(get_db)):
    """获取所有筛选规则"""
    return db.query(FilterRule).order_by(FilterRule.priority.desc()).all()


@router.post("/", response_model=FilterRuleOut)
async def create_rule(rule: FilterRuleCreate, db: Session = Depends(get_db)):
    """创建新的筛选规则"""
    existing = db.query(FilterRule).filter(FilterRule.name == rule.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Rule with name '{rule.name}' already exists")

    db_rule = FilterRule(**rule.model_dump())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    logger.info(f"Created filter rule: {rule.name}")
    return db_rule


@router.get("/{rule_id}", response_model=FilterRuleOut)
async def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """获取单个规则"""
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/{rule_id}", response_model=FilterRuleOut)
async def update_rule(rule_id: int, rule_update: FilterRuleUpdate, db: Session = Depends(get_db)):
    """更新筛选规则"""
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = rule_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)
    logger.info(f"Updated filter rule: {rule.name}")
    return rule


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """删除筛选规则"""
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()
    logger.info(f"Deleted filter rule: {rule.name}")
    return {"ok": True, "deleted": rule_id}

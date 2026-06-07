#!/usr/bin/env python3
"""
数据库初始化脚本：创建所有表，并插入默认筛选规则。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import init_db, get_session
from app.models.rule import FilterRule, RuleType

DEFAULT_KEYWORDS = [
    "admin", "api", "vpn", "portal", "oa", "dev",
    "test", "staging", "backup", "console", "dashboard",
    "login", "manage", "ops", "monitor", "grafana",
    "jenkins", "gitlab", "kibana", "k8s", "swagger",
]


def seed_default_rules():
    """插入默认关键词筛选规则"""
    with get_session() as session:
        existing = session.query(FilterRule).first()
        if existing:
            print("[init_db] Rules already exist, skipping seed.")
            return

        for kw in DEFAULT_KEYWORDS:
            rule = FilterRule(
                name=f"keyword:{kw}",
                rule_type=RuleType.KEYWORD,
                pattern=kw,
                priority=1,
                enabled=True,
            )
            session.add(rule)

        session.commit()
        print(f"[init_db] Seeded {len(DEFAULT_KEYWORDS)} default filter rules.")


if __name__ == "__main__":
    init_db()
    seed_default_rules()
    print("[init_db] Database initialized successfully.")

"""
Supabase(PostgREST)最小封装,供 telegram-bot/ 下的脚本用,只依赖 requests。
环境变量:SUPABASE_URL、SUPABASE_SERVICE_KEY(回退 SUPABASE_KEY)
"""
import os

import requests

URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY", "")
HDR = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}


def get_all(table, params):
    """分页拉全量(PostgREST 单次上限 1000 行)。params 可以是 dict 或 [(k, v), …]。"""
    rows, offset = [], 0
    while True:
        r = requests.get(f"{URL}/rest/v1/{table}", headers={**HDR, "Range": f"{offset}-{offset + 999}"},
                         params=params, timeout=30)
        r.raise_for_status()
        batch = r.json()
        rows += batch
        if len(batch) < 1000:
            return rows
        offset += 1000


def insert(table, data, upsert_on=None):
    """插入一行或多行;upsert_on 给冲突列名时按它 upsert。返回写入后的行。"""
    headers = {**HDR, "Content-Type": "application/json", "Prefer": "return=representation"}
    params = {}
    if upsert_on:
        headers["Prefer"] += ",resolution=merge-duplicates"
        params["on_conflict"] = upsert_on
    r = requests.post(f"{URL}/rest/v1/{table}", headers=headers, params=params, json=data, timeout=30)
    r.raise_for_status()
    return r.json()


def audit(action, table, record_id, detail, who="Telegram 机器人"):
    """写审计日志,失败不抛(和 utils/database.log_audit 一样永不拖垮主流程)。"""
    try:
        insert("audit_log", {"admin_name": who, "admin_role": "", "action": action,
                             "table_name": table, "record_id": str(record_id or ""),
                             "detail": str(detail)[:200]})
    except Exception:
        pass

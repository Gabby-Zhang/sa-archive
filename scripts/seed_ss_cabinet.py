#!/usr/bin/env python3
"""
导入 Stéphane Séjourné 欧委会内阁成员到 team_members 表。

数据来源：欧盟委员会官网
https://commission.europa.eu/about/organisation/college-commissioners/stephane-sejourne/stephane-sejournes-team_en

字段约定（沿用现有 team_members 表，无需改库结构）：
  person = "Stéphane Séjourné"
  team   = 分组（内阁领导 / 内阁专家 / 内阁成员 / 政策助理 / 支持团队）
  name   = 姓名
  title  = "职位 · 分管领域"（页面渲染时拆开：职位灰字、领域主色突出）
  note   = 邮箱（页面渲染成 ✉️ mailto 链接）

幂等：按 (person, name) 查重，已存在则更新，不存在则插入。可反复运行。

用法：
  python3 scripts/seed_ss_cabinet.py            # 写入数据库
  python3 scripts/seed_ss_cabinet.py --dry-run  # 只打印，不写库
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

PERSON = "Stéphane Séjourné"

# (team, name, title, email)
CABINET = [
    # ── 内阁领导 ──────────────────────────────────────────
    ("内阁领导", "Bertrand L'Huillier", "内阁主任",     "bertrand.l-huillier@ec.europa.eu"),
    ("内阁领导", "Estelle Göger",        "内阁副主任",   "estelle.goeger@ec.europa.eu"),
    # ── 内阁专家 ──────────────────────────────────────────
    ("内阁专家", "Alexandr Hobza",       "内阁专家 · 投资与创新",       "alexandr.hobza@ec.europa.eu"),
    ("内阁专家", "Aleksandra Kordecka",  "内阁专家 · 产业战略与脱碳",   "aleksandra.kordecka@ec.europa.eu"),
    # ── 内阁成员 ──────────────────────────────────────────
    ("内阁成员", "Laia Pinos Mataro",      "成员 · 能源、气候与环境",       "laia.pinos-mataro@ec.europa.eu"),
    ("内阁成员", "Dragos Tudorache",       "成员 · 经济安全与技术主权",     "ioan-dragos.tudorache@ec.europa.eu"),
    ("内阁成员", "Hanna Anttilainen",      "成员 · 单一市场与简化",         "hanna.anttilainen@ec.europa.eu"),
    ("内阁成员", "Jugatx Ortiz Gonzalez",  "成员 · 中小企业与公共采购",     "jugatx.ortiz-gonzalez@ec.europa.eu"),
    ("内阁成员", "Sacha Halphen",          "成员 · 政治顾问",               "sacha.halphen@ec.europa.eu"),
    # ── 政策助理 ──────────────────────────────────────────
    ("政策助理", "Helena Robyn",        "政策助理 · 议会顾问",           "helena.robyn@ec.europa.eu"),
    ("政策助理", "Anna Nykiel-Mateo",   "政策助理 · 卫生与社会",         "anna.nykiel@ec.europa.eu"),
    ("政策助理", "Vincent Hurkens",     "政策助理 · 金融服务",           "vincent.hurkens@ec.europa.eu"),
    # ── 支持团队 ──────────────────────────────────────────
    ("支持团队", "Arthur Corbin",          "助理 · 企业",                  "arthur.corbin@ec.europa.eu"),
    ("支持团队", "Antoine Guéry",          "传播顾问",                     "antoine.guery@ec.europa.eu"),
    ("支持团队", "Paola d'Amécourt",       "传播助理",                     "paola.d'amecourt@ec.europa.eu"),
    ("支持团队", "Sandrine Barreaux",      "文件管理专员",                 "sandrine.barreaux@ec.europa.eu"),
    ("支持团队", "Sonia Silva Capitao",    "文件管理专员",                 "sonia.silva@ec.europa.eu"),
    ("支持团队", "Nathalie Leduc",         "执行副主席助理",               "nathalie.leduc@ec.europa.eu"),
    ("支持团队", "Pauline Jannes",         "内阁主任助理",                 "pauline.jannes@ec.europa.eu"),
    ("支持团队", "Michail Stergiopoulos",  "助理",                         "michail.stergiopoulos@ec.europa.eu"),
    ("支持团队", "Miha Matoz",             "助理",                         "miha.matoz@ec.europa.eu"),
    ("支持团队", "Melissa Kizekele",       "助理",                         "melissa.kizekele@ec.europa.eu"),
]


def _load_creds():
    secrets_path = pathlib.Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        import toml
        s = toml.load(str(secrets_path))
        return s["SUPABASE_URL"], (s.get("SUPABASE_SERVICE_KEY") or s["SUPABASE_KEY"])
    import os
    return os.environ["SUPABASE_URL"], (os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写库")
    args = ap.parse_args()

    if args.dry_run:
        cur = None
        for team, name, title, email in CABINET:
            if team != cur:
                cur = team
                print(f"\n### {team}")
            print(f"  {name:24s} | {title:24s} | {email}")
        print(f"\n共 {len(CABINET)} 人（dry-run，未写库）")
        return

    from supabase import create_client
    url, key = _load_creds()
    db = create_client(url, key)

    inserted = updated = 0
    for team, name, title, email in CABINET:
        row = {"person": PERSON, "team": team, "name": name, "title": title, "note": email}
        existing = (db.table("team_members").select("id")
                    .eq("person", PERSON).eq("name", name).limit(1).execute().data) or []
        if existing:
            db.table("team_members").update(row).eq("id", existing[0]["id"]).execute()
            updated += 1
        else:
            db.table("team_members").insert(row).execute()
            inserted += 1

    print(f"完成：新增 {inserted} 人，更新 {updated} 人，共 {len(CABINET)} 人。")


if __name__ == "__main__":
    main()

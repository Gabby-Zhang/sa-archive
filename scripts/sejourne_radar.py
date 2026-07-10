#!/usr/bin/env python3
"""
Séjourné 辖区/家族「游说雷达」

背景:Stéphane Séjourné 现任欧盟委员会执行副主席·繁荣与产业战略(2024–2029)。
用邮件里搜他名字(EU Influence 近 8 期 = 0 次)会严重低估他的相关度——这份通讯
按「游说生态」写,很少点委员名。真正抓得全,要按两个维度扫:
  A) 辖区(portfolio):产业战略/竞争力/单一市场/简化去监管/中小企业/战略产业与
     原料/贸易海关采购/工业AI 标准 —— 官方分管清单见
     https://commission.europa.eu/.../stephane-sejourne_en
  B) 政治家族(family):Renew Europe 党团 / ALDE / Renaissance / 马克龙阵营 ——
     他当过 Renew Europe 党团主席,家族的廉洁/党务丑闻同样与他相关
     (如 2026-07-09 期 ALDE 药企 cash-for-access)。

用法:
    python3 scripts/sejourne_radar.py [--since-days 60] [--sender ADDR ...] [--min 3] [-v]
    # 默认扫 EU Influence 近 60 天;--sender 可重复,加 Brussels Playbook 等
    # 鉴权同 fetch_playbook_email.py:环境变量 GMAIL_USER / GMAIL_APP_PASSWORD

输出:每期一行(辖区分/家族分/判定 + 落点),命中期附证据句;末尾主题总量。
判定阈值 --min(默认 3):辖区分+家族分 >= min 记「✅相关」,>0 记「△弱」,0 记「—」。
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
FETCH = HERE / "fetch_playbook_email.py"
EXTRACT = REPO / "scheduled-tasks" / "paris-playbook-daily" / "extract_playbook.py"

# EU Influence(布鲁塞尔游说周报)。--sender 可加 brusselsplaybook@politico.eu 等。
DEFAULT_SENDERS = ["influence@politico.eu"]

# --- 复用 extract_playbook.clean_html(双重转义 HTML → 纯文本)---
_spec = importlib.util.spec_from_file_location("ep", EXTRACT)
ep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ep)

# A) 辖区词表(据欧委会官方 portfolio)
PORTFOLIO = {
    "产业战略/去碳":  r"industrial strateg|industrial polic|industrial decarbon|net[- ]zero industry|clean industrial deal|reindustrial|IPCEI|important projects of common",
    "单一市场":       r"single market|internal market",
    "竞争力/基金":    r"competitiv|competitiveness fund|draghi",
    "简化/去监管":    r"simplif|omnibus|red tape|deregulat|better regulation|regulatory burden|cut(?:ting)? red",
    "中小企业/投资":  r"\bSME\b|small business|mid[- ]?cap|scale[- ]?up|start[- ]?up|access to finance|savings and investment union",
    "战略产业/原料":  r"critical raw material|raw material|semiconduct|\bchips?\b|steel|automotive|batter|defen[cs]e industr|clean ?tech|supply chain",
    "贸易/海关/采购": r"customs|foreign subsid|public procurement|procurement|trade defen|tariff|anti[- ]?dumping",
    "工业AI/标准":    r"industrial AI|AI Act|standardi[sz]ation|standard-setting",
}
# B) 政治家族词表(Renew / ALDE / Renaissance / 马克龙阵营)
FAMILY = {
    "政治家族/Renew": r"\bRenew\b|\bALDE\b|Renaissance|liberals?[’'\s]s?\s?(?:party|group|congress|bash|shindig)|\bcentrist|Macron",
}
ALL = {**PORTFOLIO, **FAMILY}


def fetch(senders, since_days):
    """跑 fetch_playbook_email.py(每个 sender 一次)拿 messages,套 120s 硬超时
    防 IMAP 挂起。合并去重(按 subject+date)。"""
    msgs, seen = [], set()
    for sender in senders:
        try:
            out = subprocess.run(
                ["perl", "-e", "alarm 120; exec @ARGV or exit 127",
                 sys.executable, str(FETCH), "--sender", sender,
                 "--since-days", str(since_days)],
                capture_output=True, text=True, timeout=140,
            )
        except subprocess.TimeoutExpired:
            print(f"⚠️  抓 {sender} 超时,跳过", file=sys.stderr)
            continue
        if out.returncode != 0:
            print(f"⚠️  抓 {sender} 失败(rc={out.returncode}):{out.stderr.strip()[:200]}",
                  file=sys.stderr)
            continue
        try:
            data = json.loads(out.stdout)
        except json.JSONDecodeError:
            print(f"⚠️  {sender} 输出非 JSON,跳过", file=sys.stderr)
            continue
        for m in data.get("messages", []):
            k = (m.get("subject", ""), m.get("date", ""))
            if k not in seen:
                seen.add(k)
                msgs.append(m)
    return sorted(msgs, key=lambda x: x.get("date", ""))


def score(text, table):
    return {t: len(re.findall(p, text, re.I)) for t, p in table.items()}


def evidence(text, table, per, limit=3):
    """按命中主题挑几句证据(含关键词、长度>40 的句子)。"""
    hot = re.compile("|".join(p for t, p in table.items() if per[t]), re.I)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if s.strip()]
    out = []
    for s in sents:
        if len(s) > 40 and hot.search(s):
            out.append(s[:280])
        if len(out) >= limit:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-days", type=int, default=60)
    ap.add_argument("--sender", action="append", default=None,
                    help="可重复;默认 EU Influence")
    ap.add_argument("--min", type=int, default=3, help="判定「相关」的合并分阈值")
    ap.add_argument("-v", "--verbose", action="store_true", help="打印证据句")
    args = ap.parse_args()

    senders = args.sender or DEFAULT_SENDERS
    msgs = fetch(senders, args.since_days)
    if not msgs:
        print("没抓到邮件(检查 GMAIL_USER/GMAIL_APP_PASSWORD、sender、时间窗)。")
        return

    agg = {t: 0 for t in ALL}
    rel = 0
    print(f"扫 {len(msgs)} 期(sender: {', '.join(senders)},近 {args.since_days} 天)\n")
    for m in msgs:
        text = ep.clean_html(m.get("htmlBody", "") or m.get("plaintextBody", ""))
        date = m.get("date", "")[:10]
        subj = m.get("subject", "")[:46]
        pf, fam = score(text, PORTFOLIO), score(text, FAMILY)
        per = {**pf, **fam}
        for t, n in per.items():
            agg[t] += n
        ps, fs = sum(pf.values()), sum(fam.values())
        tot = ps + fs
        flag = "✅相关" if tot >= args.min else ("△弱" if tot else "—无")
        if tot >= args.min:
            rel += 1
        top = ", ".join(f"{t}×{n}" for t, n in sorted(per.items(), key=lambda x: -x[1]) if n)
        print(f"{date}  辖区={ps:2d} 家族={fs:2d}  {flag}  | {subj}")
        if top:
            print(f"            落点: {top}")
        if args.verbose and tot:
            for s in evidence(text, ALL, per):
                print(f"              • {s}")
        print()

    print(f"— 相关(合并分≥{args.min}): {rel}/{len(msgs)} 期 —")
    print("主题总量:")
    for t, n in sorted(agg.items(), key=lambda x: -x[1]):
        if n:
            print(f"  {n:3d}  {t}")


if __name__ == "__main__":
    main()

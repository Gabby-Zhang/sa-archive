"""
数据导入脚本 — 从腾讯文档导出的 Excel 导入 Supabase
使用方法：python3 import_data.py /path/to/SA档案馆.xlsx
"""
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta
import streamlit as st
from utils.database import get_supabase

# ── 工具函数 ─────────────────────────────────────────────
def get_shared_strings(z):
    ss_xml = z.read('xl/sharedStrings.xml')
    root = ET.fromstring(ss_xml)
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    strings = []
    for si in root.findall(f'{{{ns}}}si'):
        text = ''.join(t.text or '' for t in si.iter(f'{{{ns}}}t'))
        strings.append(text)
    return strings

def excel_date(n):
    """将 Excel 日期数字转换为 ISO 日期字符串"""
    try:
        n = int(float(n))
        return (date(1899, 12, 30) + timedelta(days=n)).isoformat()
    except Exception:
        return None

def read_sheet_raw(z, sheet_file, shared_strings):
    """读取 sheet，返回 {列字母: 值} 的列表"""
    xml_data = z.read(f'xl/worksheets/{sheet_file}')
    root = ET.fromstring(xml_data)
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rows = []
    for row_el in root.findall(f'.//{{{ns}}}row'):
        row_data = {}
        for cell in row_el.findall(f'{{{ns}}}c'):
            ref = cell.get('r', '')
            col = ''.join(c for c in ref if c.isalpha())
            t = cell.get('t', '')
            v_el = cell.find(f'{{{ns}}}v')
            val = ''
            if v_el is not None and v_el.text:
                val = shared_strings[int(v_el.text)] if t == 's' else v_el.text
            row_data[col] = val
        if any(row_data.values()):
            rows.append(row_data)
    return rows

def normalize_person(char):
    mapping = {
        'SS': 'Stéphane Séjourné',
        'GA': 'Gabriel Attal',
        'ss': 'Stéphane Séjourné',
        'ga': 'Gabriel Attal',
        '两人': '两人',
        'SS&GA': '两人',
        'GA&SS': '两人',
    }
    return mapping.get(char.strip(), char.strip())

# ── 导入大事记 ────────────────────────────────────────────
def import_events(z, shared, db):
    rows = read_sheet_raw(z, 'sheet1.xml', shared)
    events = []
    header_passed = False

    for row in rows:
        # 跳过说明行，找到真正的数据（Year 列为数字年份）
        year = row.get('A', '').strip()
        if year == 'Year':
            header_passed = True
            continue
        if not header_passed:
            continue

        char = row.get('C', '').strip()
        if not char:
            continue

        # 日期处理
        date_raw = row.get('B', '').strip()
        if date_raw and date_raw not in ('\\', ''):
            date_str = excel_date(date_raw) or year
        else:
            date_str = year  # 只有年份

        # 事件描述（D列），来源（E列），备注（F列）
        event = row.get('D', '').strip()
        source = row.get('E', '').strip()
        remark = row.get('F', '').strip()

        if not event:
            continue

        events.append({
            'date': date_str,
            'person': normalize_person(char),
            'title': event[:500],
            'source': source[:300] if source else '',
            'note': remark[:300] if remark else '',
        })

    print(f'准备导入 {len(events)} 条大事记…')
    # 分批插入
    batch_size = 50
    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        db.table('events').insert(batch).execute()
        print(f'  已导入 {min(i+batch_size, len(events))}/{len(events)}')
    print('大事记导入完成！')
    return len(events)

# ── 导入 SS 内阁 ─────────────────────────────────────────
def import_cabinet(z, shared, db):
    rows = read_sheet_raw(z, 'sheet5.xml', shared)
    members = []
    for row in rows[1:]:  # 跳过标题行
        name = row.get('B', '').strip()
        title = row.get('C', '').strip()
        note = row.get('D', '').strip()
        if not name:
            continue
        members.append({
            'person': 'Stéphane Séjourné',
            'team': 'EVP内阁',
            'name': name,
            'title': title,
            'note': note,
        })
    print(f'准备导入 {len(members)} 条 SS 内阁成员…')
    if members:
        db.table('team_members').insert(members).execute()
    print('SS 内阁导入完成！')
    return len(members)

# ── 导入 GA 团队 ─────────────────────────────────────────
def import_ga_team(z, shared, db):
    rows = read_sheet_raw(z, 'sheet6.xml', shared)
    members = []
    current_team = 'GA团队'
    for row in rows:
        team_label = row.get('A', '').strip()
        if team_label:
            current_team = team_label.split('\n')[0]
        name = row.get('B', '').strip()
        title = row.get('C', '').strip()
        note = row.get('D', '').strip()
        if not name:
            continue
        members.append({
            'person': 'Gabriel Attal',
            'team': current_team,
            'name': name,
            'title': title,
            'note': note,
        })
    print(f'准备导入 {len(members)} 条 GA 团队成员…')
    if members:
        db.table('team_members').insert(members).execute()
    print('GA 团队导入完成！')
    return len(members)

# ── 主程序 ───────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print('用法：python3 import_data.py /path/to/SA档案馆.xlsx')
        sys.exit(1)

    filepath = sys.argv[1]
    print(f'读取文件：{filepath}')

    # 需要 Supabase 连接
    # 在部署后通过 Streamlit 界面导入更方便
    # 这里保留命令行导入逻辑备用

    with zipfile.ZipFile(filepath) as z:
        shared = get_shared_strings(z)
        try:
            db = get_supabase()
            n1 = import_events(z, shared, db)
            n2 = import_cabinet(z, shared, db)
            n3 = import_ga_team(z, shared, db)
            print(f'\n✅ 导入完成！共 {n1+n2+n3} 条记录')
        except Exception as e:
            print(f'❌ 导入失败：{e}')
            print('请确认 .streamlit/secrets.toml 已配置正确的 Supabase 凭据')

if __name__ == '__main__':
    main()

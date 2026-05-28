import streamlit as st

st.set_page_config(page_title="选举参考 · 档案馆", page_icon="🗳️", layout="wide")

st.title("🗳️ 法国选举制度参考")
st.caption("法国各类选举类型说明")

elections = [
    {
        "name": "总统大选",
        "fr": "Élection présidentielle",
        "rep": "总统",
        "term": "5年",
        "type": "直接普选",
        "note": "两轮制，第一轮超50%直接当选，否则前两名进入第二轮"
    },
    {
        "name": "立法选举",
        "fr": "Élection législative",
        "rep": "国民议会议员（共577席）",
        "term": "5年",
        "type": "直接普选",
        "note": "两轮制，选区单一席位。GA 代表上塞纳省第10选区"
    },
    {
        "name": "参议院选举",
        "fr": "Élection sénatoriale",
        "rep": "参议员（共348席）",
        "term": "6年（每3年改选一半）",
        "type": "间接普选",
        "note": "由地方选举产生的代表团选举"
    },
    {
        "name": "欧洲议会选举",
        "fr": "Élection européenne",
        "rep": "欧洲议员（法国81席）",
        "term": "5年",
        "type": "直接普选",
        "note": "比例代表制，全国单一选区。SS和GA均曾参与欧选相关活动"
    },
    {
        "name": "地区选举",
        "fr": "Élection régionale",
        "rep": "大区议员",
        "term": "6年",
        "type": "直接普选",
        "note": "两轮制，比例代表"
    },
    {
        "name": "市政选举",
        "fr": "Élection municipale",
        "rep": "市政委员",
        "term": "6年",
        "type": "直接普选",
        "note": "1000人以上市镇采用比例两轮制"
    },
    {
        "name": "市长选举",
        "fr": "Élection des maires",
        "rep": "市长",
        "term": "6年",
        "type": "间接（由市政委员互选）",
        "note": "市政选举后由当选委员互选产生"
    },
    {
        "name": "行政区选举",
        "fr": "Élection cantonale / départementale",
        "rep": "省议员",
        "term": "6年（每3年改选一半）",
        "type": "直接普选",
        "note": "两轮制，每个选区选一男一女"
    },
]

for e in elections:
    with st.container():
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"""
            <div style="background:var(--cb);border-left:4px solid #4A90D9;
                        padding:1rem;border-radius:0 8px 8px 0;margin-bottom:0.8rem">
                <div style="color:#4A90D9;font-size:1.1rem;font-weight:bold">{e['name']}</div>
                <div style="color:#888;font-size:0.85rem;font-style:italic">{e['fr']}</div>
                <div style="margin-top:0.5rem">
                    <span style="background:var(--cb2);padding:0.2rem 0.5rem;border-radius:4px;
                                 color:#7EC8A4;font-size:0.8rem">{e['type']}</span>
                    <span style="color:#aaa;font-size:0.85rem;margin-left:0.8rem">任期：{e['term']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div style="background:var(--cb);padding:1rem;border-radius:8px;
                        margin-bottom:0.8rem;height:100%">
                <div style="color:var(--t1);margin-bottom:0.3rem">
                    <span style="color:#888;font-size:0.85rem">所选代表：</span> {e['rep']}
                </div>
                <div style="color:#bbb;font-size:0.9rem">{e['note']}</div>
            </div>
            """, unsafe_allow_html=True)

st.divider()
st.caption("💡 提示：法国实行两轮投票制（scrutin à deux tours），在大多数选举中广泛使用")

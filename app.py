import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import datetime

st.set_page_config(page_title="rubyohoto 収支管理", layout="wide")

# --- 設定：保存用スプレッドシートのURL（裏側で勝手に使います） ---
SHEET_URL = "ここにスプレッドシートのURLを貼る"

# 接続設定
conn = st.connection("gsheets", type=GSheetsConnection)

def load_df(worksheet):
    try: return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet, ttl="0s")
    except: return pd.DataFrame()

# 1. カメラマン（ここを固定にしたので、もう消えません）
current_member_list = ["森さん", "宇田さん", "三沖さん", "野澤さん"]
m_df = load_df("master")
if m_df.empty:
    m_df = pd.DataFrame([
        {"氏名": "森さん", "日給": 15000, "目標SKU": 15},
        {"氏名": "宇田さん", "日給": 14300, "目標SKU": 14},
        {"氏名": "三沖さん", "日給": 13000, "目標SKU": 12},
        {"氏 name": "野澤さん", "日給": 13000, "目標SKU": 12}
    ])
master_dict = m_df.set_index("氏名").to_dict("index")

# 2. ブランド単価
b_df = load_df("brands")
if b_df.empty:
    b_df = pd.DataFrame([{"ブランド名": "ブランドA", "SKU単価": 1900}, {"ブランド名": "ブランドB", "SKU単価": 2500}])
brand_dict = b_df.set_index("ブランド名")["SKU単価"].to_dict()

# 3. 撮影実績
sku_db = load_df("sku")

# --- 画面構成 ---
st.sidebar.header("📅 期間選択")
month_focus = st.sidebar.selectbox("対象月", ["2026/05", "2026/06", "2026/07"])
period_focus = st.sidebar.radio("期間区分", ["第1期 (1-20日)", "第2期 (21-末日)"])
full_p_label = f"{month_focus} {period_focus}"

tab1, tab2, tab3 = st.tabs(["📉 収支分析", "📝 実績入力", "⚙️ 各種設定"])

# --- タブ1：収支分析 ---
with tab1:
    if not sku_db.empty:
        sku_db['日付'] = pd.to_datetime(sku_db['日付'], errors='coerce')
        def get_p(d): return f"{d.year}/{d.month:02d} {'第1期 (1-20日)' if d.day <= 20 else '第2期 (21-末日)'}"
        sku_db['判定'] = sku_db['日付'].apply(lambda x: get_p(x) if pd.notnull(x) else "")
        target = sku_db[sku_db['判定'] == full_p_label].copy()
        
        if not target.empty:
            target['売上'] = target.apply(lambda x: x['実績SKU'] * brand_dict.get(x['ブランド'], 0), axis=1)
            sum_s = target.groupby('氏名')['実績SKU', '売上'].sum().reset_index()
            final = pd.merge(pd.DataFrame({"氏名": current_member_list}), sum_s, on='氏名', how='left').fillna(0)
            
            def calc_biz(row):
                m = master_dict.get(row['氏名'], {"日給":0})
                cost = m['日給'] if row['実績SKU'] > 0 else 0
                return pd.Series([cost, row['売上'] - cost])
            
            final[['原価', '利益']] = final.apply(calc_biz, axis=1)
            final['氏名'] = pd.Categorical(final['氏名'], categories=current_member_list, ordered=True)
            final = final.sort_values('氏名')

            m1, m2, m3 = st.columns(3)
            m1.metric("総売上", f"¥{int(final['売上'].sum()):,}")
            m2.metric("総原価", f"¥{int(final['原価'].sum()):,}")
            m3.metric("粗利益", f"¥{int(final['利益'].sum()):,}")

            st.bar_chart(final.set_index('氏名')['利益'])
            st.dataframe(final.style.format({"売上": "¥{:,.0f}", "原価": "¥{:,.0f}", "利益": "¥{:,.0f}"}), use_container_width=True, hide_index=True)
    else:
        st.info("データがありません")

# --- タブ2：入力（ここで裏側に保存されます） ---
with tab2:
    st.subheader("実績の追加")
    with st.form("add_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        d_date = c1.date_input("撮影日", datetime.date.today())
        d_name = c2.selectbox("カメラマン", current_member_list)
        d_brand = c3.selectbox("ブランド", list(brand_dict.keys()))
        d_sku = c4.number_input("SKU数", min_value=0)
        if st.form_submit_button("保存"):
            new_data = pd.DataFrame([{"日付": str(d_date), "氏名": d_name, "ブランド": d_brand, "実績SKU": d_sku}])
            sku_db = pd.concat([sku_db, new_data], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="sku", data=sku_db)
            st.success("保存完了")
            st.rerun()
    
    if not sku_db.empty:
        st.write("▼ 実績データ")
        ed_sku = st.data_editor(sku_db, num_rows="dynamic", use_container_width=True)
        if st.button("実績を修正・削除"):
            conn.update(spreadsheet=SHEET_URL, worksheet="sku", data=ed_sku)
            st.rerun()

# --- タブ3：設定 ---
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👥 カメラマン設定")
        ed_m = st.data_editor(m_df, hide_index=True)
        if st.button("カメラマン情報を保存"):
            conn.update(spreadsheet=SHEET_URL, worksheet="master", data=ed_m)
    with col2:
        st.subheader("🏷️ ブランド単価設定")
        ed_b = st.data_editor(b_df, num_rows="dynamic", hide_index=True)
        if st.button("ブランド情報を保存"):
            conn.update(spreadsheet=SHEET_URL, worksheet="brands", data=ed_b)

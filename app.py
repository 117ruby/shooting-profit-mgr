import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import datetime

st.set_page_config(page_title="rubyohoto 収支管理", layout="wide")

# --- 設定：共有いただいたスプレッドシートのURL ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1cEb3xBs1YcrmanfCkDOWtIpHddC6AdOWqkDLcNgLzJM/edit?usp=sharing"

# 接続設定
conn = st.connection("gsheets", type=GSheetsConnection)

def load_df(worksheet):
    try:
        # 最新データを取得
        return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet, ttl="0s")
    except Exception as e:
        st.error(f"シート '{worksheet}' の読み込みに失敗しました。1行目に項目名が入っているか確認してください。")
        return pd.DataFrame()

# 1. カメラマン固定（マスタ）
current_member_list = ["森さん", "宇田さん", "三沖さん", "野澤さん"]
m_df = load_df("master")
if m_df.empty:
    m_df = pd.DataFrame([
        {"氏名": "森さん", "日給": 15000, "目標SKU": 15},
        {"氏名": "宇田さん", "日給": 14300, "目標SKU": 14},
        {"氏名": "三沖さん", "日給": 13000, "目標SKU": 12},
        {"氏名": "野澤さん", "日給": 13000, "目標SKU": 12}
    ])
master_dict = m_df.set_index("氏名").to_dict("index")

# 2. 実績データ
sku_db = load_df("sku")

# --- 画面構成 ---
st.sidebar.header("📅 期間選択")
month_focus = st.sidebar.selectbox("対象月", ["2026/05", "2026/06", "2026/07"])
period_focus = st.sidebar.radio("期間区分", ["第1期 (1-20日)", "第2期 (21-末日)"])
full_p_label = f"{month_focus} {period_focus}"

tab1, tab2, tab3 = st.tabs(["📉 収支分析", "📝 実績入力", "⚙️ 設定"])

# --- タブ1：収支分析 ---
with tab1:
    st.header(f"📊 {full_p_label} レポート")
    unit_price = st.number_input("共通SKU単価 (円)", value=2000)
    
    if not sku_db.empty:
        sku_db['日付'] = pd.to_datetime(sku_db['日付'], errors='coerce')
        def get_p(d): return f"{d.year}/{d.month:02d} {'第1期 (1-20日)' if d.day <= 20 else '第2期 (21-末日)'}"
        sku_db['判定'] = sku_db['日付'].apply(lambda x: get_p(x) if pd.notnull(x) else "")
        target = sku_db[sku_db['判定'] == full_p_label].copy()
        
        if not target.empty:
            sum_s = target.groupby('氏名')['実績SKU'].sum().reset_index()
            final = pd.merge(pd.DataFrame({"氏名": current_member_list}), sum_s, on='氏名', how='left').fillna(0)
            
            def calc_biz(row):
                m = master_dict.get(row['氏名'], {"日給":0})
                sales = row['実績SKU'] * unit_price
                cost = m['日給'] if row['実績SKU'] > 0 else 0
                return pd.Series([sales, cost, sales - cost])
            
            final[['売上', '原価', '利益']] = final.apply(calc_biz, axis=1)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("総売上", f"¥{int(final['売上'].sum()):,}")
            c2.metric("総原価", f"¥{int(final['原価'].sum()):,}")
            c3.metric("粗利益", f"¥{int(final['利益'].sum()):,}")

            st.bar_chart(final.set_index('氏名')['利益'])
            st.dataframe(final.style.format({"売上": "¥{:,.0f}", "原価": "¥{:,.0f}", "利益": "¥{:,.0f}"}), use_container_width=True, hide_index=True)
    else:
        st.info("実績データがまだありません。")

# --- タブ2：入力 ---
with tab2:
    st.subheader("撮影実績の追加")
    with st.form("add_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        d_date = c1.date_input("撮影日", datetime.date.today())
        d_name = c2.selectbox("カメラマン", current_member_list)
        d_sku = c3.number_input("実績SKU", min_value=0)
        d_brand = st.text_input("ブランド名")
        
        if st.form_submit_button("スプレッドシートへ保存"):
            new_data = pd.DataFrame([{"日付": str(d_date), "氏名": d_name, "ブランド": d_brand, "実績SKU": d_sku}])
            # 既存データと結合して上書き保存
            updated_df = pd.concat([sku_db, new_data], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="sku", data=updated_df)
            st.success("スプレッドシートに保存しました！")
            st.rerun()

    if not sku_db.empty:
        st.divider()
        st.write("▼ 登録済みデータ（修正して保存ボタンで反映）")
        ed_sku = st.data_editor(sku_db, num_rows="dynamic", use_container_width=True)
        if st.button("実績データを一括更新"):
            conn.update(spreadsheet=SHEET_URL, worksheet="sku", data=ed_sku)
            st.success("更新しました。")

# --- タブ3：設定 ---
with tab3:
    st.subheader("カメラマン単価設定")
    ed_m = st.data_editor(m_df, hide_index=True)
    if st.button("マスター情報を保存"):
        conn.update(spreadsheet=SHEET_URL, worksheet="master", data=ed_m)
        st.success("マスターを更新しました。")

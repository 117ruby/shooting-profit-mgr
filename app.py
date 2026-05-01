import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

st.set_page_config(page_title="rubyohoto 収支管理", layout="wide")

# --- 設定：共有いただいたスプレッドシートのURLを直接指定 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1cEb3xBs1YcrmanfCkDOWtIpHddC6AdOWqkDLcNgLzJM/edit?usp=sharing"

# 接続設定
conn = st.connection("gsheets", type=GSheetsConnection)

def load_df(worksheet):
    try:
        # 最新データを取得
        return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet, ttl="0s")
    except Exception as e:
        st.error(f"シート '{worksheet}' の読み込みに失敗しました。シート名や共有設定を確認してください。")
        return pd.DataFrame()

# 1. カメラマンマスタの読み込み
m_df = load_df("master")
if m_df.empty:
    # データがない場合の初期値（ここで個人ごとの単価を設定できるようにしました）
    m_df = pd.DataFrame([
        {"氏名": "森さん", "日給": 15000, "SKU単価": 2000, "目標SKU": 15},
        {"氏名": "宇田さん", "日給": 14300, "SKU単価": 2000, "目標SKU": 14},
        {"氏名": "三沖さん", "日給": 13000, "SKU単価": 2000, "目標SKU": 12},
        {"氏名": "野澤さん", "日給": 13000, "SKU単価": 2000, "目標SKU": 12}
    ])
master_dict = m_df.set_index("氏名").to_dict("index")
current_member_list = m_df["氏名"].tolist()

# 2. 実績データの読み込み
sku_db = load_df("sku")

# --- 画面構成 ---
st.sidebar.header("📅 期間選択")
month_focus = st.sidebar.selectbox("対象月", ["2026/05", "2026/06"])
period_focus = st.sidebar.radio("期間区分", ["第1期 (1-20日)", "第2期 (21-末日)"])
full_p_label = f"{month_focus} {period_focus}"

tab1, tab2, tab3 = st.tabs(["📉 収支分析", "📝 実績入力", "⚙️ 設定"])

# --- タブ1：収支分析（共通単価を消して自動計算にしました） ---
with tab1:
    st.header(f"📊 {full_p_label} レポート")
    
    if not sku_db.empty:
        sku_db['日付'] = pd.to_datetime(sku_db['日付'], errors='coerce')
        def get_p(d): return f"{d.year}/{d.month:02d} {'第1期 (1-20日)' if d.day <= 20 else '第2期 (21-末日)'}"
        sku_db['判定'] = sku_db['日付'].apply(lambda x: get_p(x) if pd.notnull(x) else "")
        target = sku_db[sku_db['判定'] == full_p_label].copy()
        
        if not target.empty:
            sum_s = target.groupby('氏名')['実績SKU'].sum().reset_index()
            final = pd.merge(pd.DataFrame({"氏名": current_member_list}), sum_s, on='氏名', how='left').fillna(0)
            
            def calc_biz(row):
                # マスタから各個人の「日給」と「SKU単価」を取得して計算
                m = master_dict.get(row['氏名'], {"日給":0, "SKU単価": 2000})
                sales = row['実績SKU'] * m.get('SKU単価', 2000)
                cost = m['日給'] if row['実績SKU'] > 0 else 0
                return pd.Series([sales, cost, sales - cost])
            
            final[['売上', '原価', '利益']] = final.apply(calc_biz, axis=1)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("総売上", f"¥{int(final['売上'].sum()):,}")
            c2.metric("総原価", f"¥{int(final['原価'].sum()):,}")
            c3.metric("粗利益", f"¥{int(final['利益'].sum()):,}")

            st.dataframe(final.style.format({"売上": "¥{:,.0f}", "原価": "¥{:,.0f}", "利益": "¥{:,.0f}"}), use_container_width=True, hide_index=True)
    else:
        st.info("実績データがまだありません。実績入力タブから入力してください。")

# --- タブ2：入力（フォームを整理しました） ---
with tab2:
    st.subheader("📝 撮影実績の追加")
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d_date = c1.date_input("撮影日", datetime.date.today())
        d_name = c2.selectbox("カメラマン", current_member_list)
        c3, c4 = st.columns(2)
        d_brand = c3.text_input("ブランド名")
        d_sku = c4.number_input("実績SKU", min_value=0)
        
        if st.form_submit_button("スプレッドシートへ保存"):
            new_data = pd.DataFrame([{"日付": str(d_date), "氏名": d_name, "ブランド": d_brand, "実績SKU": d_sku}])
            updated_df = pd.concat([sku_db, new_data], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="sku", data=updated_df)
            st.success("スプレッドシートに保存しました！")
            st.rerun()

# --- タブ3：設定（カメラマンごとの単価をここで管理できます） ---
with tab3:
    st.subheader("⚙️ カメラマン設定")
    st.write("各カメラマンの単価や日給を修正して保存できます。")
    ed_m = st.data_editor(m_df, hide_index=True)
    if st.button("設定をスプレッドシートへ保存"):
        conn.update(spreadsheet=SHEET_URL, worksheet="master", data=ed_m)
        st.success("マスター情報を更新しました。")

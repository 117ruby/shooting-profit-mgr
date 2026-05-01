import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="rubyohoto 収支管理", layout="wide")

# --- 1. あの時の「各種設定」をアプリ内に完全保存 ---
# カメラマン設定
if 'm_df' not in st.session_state:
    st.session_state.m_df = pd.DataFrame([
        {"氏名": "森さん", "日給": 15000, "目標SKU": 15},
        {"氏名": "宇田さん", "日給": 14300, "目標SKU": 14},
        {"氏名": "三沖さん", "日給": 13000, "目標SKU": 12},
        {"氏名": "野澤さん", "日給": 13000, "目標SKU": 12}
    ])

# ブランド・単価設定（18.36.18の数値をそのまま反映）
if 'b_df' not in st.session_state:
    st.session_state.b_df = pd.DataFrame([
        {"ブランド名": "VW(モデル)", "SKU単価": 2150},
        {"ブランド名": "VW(トルソー)", "SKU単価": 3500},
        {"ブランド名": "MKOL", "SKU単価": 1500},
        {"ブランド名": "DS", "SKU単価": 700},
        {"ブランド名": "VAL", "SKU単価": 1100},
        {"ブランド名": "BP", "SKU単価": 600},
        {"ブランド名": "HK", "SKU単価": 700},
        {"ブランド名": "MJ", "SKU単価": 1850}
    ])

# 撮影実績データ
if 'sku_db' not in st.session_state:
    st.session_state.sku_db = pd.DataFrame(columns=["日付", "氏名", "ブランド名", "実績SKU"])

# --- 画面構成 ---
st.title("📸 rubyohoto 撮影収支管理")

tab1, tab2, tab3 = st.tabs(["📉 収支分析", "📝 実績入力", "⚙️ 各種設定"])

# --- タブ3：各種設定（あのスクリーンショットを再現） ---
with tab3:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("👥 カメラマン設定")
        st.session_state.m_df = st.data_editor(st.session_state.m_df, hide_index=True, key="edit_m")
    with col_b:
        st.subheader("🏷️ ブランド・単価設定")
        st.session_state.b_df = st.data_editor(st.session_state.b_df, hide_index=True, key="edit_b")

# --- タブ2：実績入力 ---
with tab2:
    st.header("📝 実績入力")
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d_date = c1.date_input("撮影日", datetime.date.today())
        d_name = c2.selectbox("カメラマン", st.session_state.m_df["氏名"].tolist())
        
        c3, c4 = st.columns(2)
        d_brand = c3.selectbox("ブランド", st.session_state.b_df["ブランド名"].tolist())
        d_sku = c4.number_input("実績SKU数", min_value=0, step=1)
        
        if st.form_submit_button("データを追加保存"):
            new_row = pd.DataFrame([{"日付": d_date, "氏名": d_name, "ブランド名": d_brand, "実績SKU": d_sku}])
            st.session_state.sku_db = pd.concat([st.session_state.sku_db, new_row], ignore_index=True)
            st.success(f"{d_name}さんのデータを追加しました！")

# --- タブ1：収支分析（ブランド別単価で精密計算） ---
with tab1:
    st.header("📊 収支分析レポート")
    if not st.session_state.sku_db.empty:
        # 実績にブランド単価を紐付け
        report_df = pd.merge(st.session_state.sku_db, st.session_state.b_df, on="ブランド名", how="left")
        report_df['売上'] = report_df['実績SKU'] * report_df['SKU単価']
        
        # カメラマンごとに集計
        summary = report_df.groupby('氏名').agg({'実績SKU': 'sum', '売上': 'sum'}).reset_index()
        final = pd.merge(st.session_state.m_df, summary, on='氏名', how='left').fillna(0)
        
        # 利益計算（日給を引く）
        final['利益'] = final.apply(lambda r: r['売上'] - r['日給'] if r['実績SKU'] > 0 else 0, axis=1)
        
        # 数字の表示
        c1, c2, c3 = st.columns(3)
        c1.metric("総売上", f"¥{int(final['売上'].sum()):,}")
        c2.metric("総人件費", f"¥{int(final[final['実績SKU']>0]['日給'].sum()):,}")
        c3.metric("粗利益", f"¥{int(final['利益'].sum()):,}")
        
        st.dataframe(final[['氏名', '実績SKU', '目標SKU', '売上', '利益']].style.format({"売上": "¥{:,.0f}", "利益": "¥{:,.0f}"}), use_container_width=True, hide_index=True)
    else:
        st.info("データがありません。「実績入力」から追加してください。")

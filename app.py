import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="rubyohoto 収支管理", layout="wide")

# --- 1. データの初期化 (session_stateで保持) ---
if 'm_df' not in st.session_state:
    st.session_state.m_df = pd.DataFrame([
        {"氏名": "森さん", "日給": 15000, "目標SKU": 15},
        {"氏名": "宇田さん", "日給": 14300, "目標SKU": 14},
        {"氏名": "三沖さん", "日給": 13000, "目標SKU": 12},
        {"氏名": "野澤さん", "日給": 13000, "目標SKU": 12}
    ])

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

if 'shift_df' not in st.session_state:
    st.session_state.shift_df = pd.DataFrame([
        {"氏名": "森さん", "期間": "2026/05 第1期 (1-20日)", "シフト日数": 6, "交通費": 816},
        {"氏名": "宇田さん", "期間": "2026/05 第1期 (1-20日)", "シフト日数": 4, "交通費": 0},
        {"氏名": "三沖さん", "期間": "2026/05 第1期 (1-20日)", "シフト日数": 3, "交通費": 0},
        {"氏名": "野澤さん", "期間": "2026/05 第1期 (1-20日)", "シフト日数": 1, "交通費": 0}
    ])

if 'sku_db' not in st.session_state:
    # 「総カット数」を完全に削除
    st.session_state.sku_db = pd.DataFrame(columns=["日付", "氏名", "ブランド", "実績SKU"])

st.title("📸 rubyohoto 撮影収支管理")

tab1, tab2, tab3 = st.tabs(["📉 収支分析", "📝 実績入力・コスト設定", "⚙️ 各種設定"])

# --- タブ1：収支分析 (グラフと集計) ---
with tab1:
    st.header("📊 収支分析レポート")
    
    # 計算：実績とブランド単価を紐付け
    calc_df = pd.merge(st.session_state.sku_db, st.session_state.b_df, left_on="ブランド", right_on="ブランド名", how="left")
    calc_df['売上金額'] = calc_df['実績SKU'] * calc_df['SKU単価'].fillna(0)
    
    summary = calc_df.groupby('氏名').agg({'実績SKU': 'sum', '売上金額': 'sum'}).reset_index()
    
    # シフトコストと合体
    final = pd.merge(st.session_state.m_df, summary, on='氏名', how='left').fillna(0)
    final = pd.merge(final, st.session_state.shift_df[['氏名', 'シフト日数', '交通費']], on='氏名', how='left').fillna(0)
    
    # 利益 = 売上 - (日給 * シフト日数 + 交通費)
    final['原価合計'] = (final['日給'] * final['シフト日数']) + final['交通費']
    final['利益'] = final['売上金額'] - final['原価合計']

    # メトリクス表示
    c1, c2, c3 = st.columns(3)
    c1.metric("総売上", f"¥{int(final['売上金額'].sum()):,}")
    c2.metric("総原価", f"¥{int(final['原価合計'].sum()):,}")
    c3.metric("粗利益", f"¥{int(final['利益'].sum()):,}")

    st.write("---")
    st.subheader("💰 カメラマン別 粗利益（グラフ）")
    st.bar_chart(final.set_index('氏名')['利益'])

    st.subheader("📋 詳細データ")
    st.dataframe(
        final[['氏名', '実績SKU', '目標SKU', '売上金額', '利益']].rename(columns={'売上金額':'売上'}),
        use_container_width=True, hide_index=True
    )

# --- タブ2：実績入力・コスト設定 ---
with tab2:
    st.subheader("❶ シフト・コスト設定")
    st.session_state.shift_df = st.data_editor(st.session_state.shift_df, hide_index=True, key="sh_ed")
    
    st.divider()
    
    st.subheader("❷ 実績入力")
    with st.container(border=True):
        # カット数を削除し、列を調整
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        in_date = col1.date_input("撮影日", datetime.date.today())
        in_name = col2.selectbox("カメラマン", st.session_state.m_df["氏名"].tolist())
        in_brand = col3.selectbox("ブランド", st.session_state.b_df["ブランド名"].tolist())
        in_sku = col4.number_input("SKU数", min_value=0, step=1)
        
        if st.button("実績を追加して保存", use_container_width=True):
            new_row = pd.DataFrame([{"日付": str(in_date), "氏名": in_name, "ブランド": in_brand, "実績SKU": in_sku}])
            st.session_state.sku_db = pd.concat([st.session_state.sku_db, new_row], ignore_index=True)
            st.rerun()

    st.subheader("▼ 実績リスト（修正・削除可能）")
    # 入力したデータが即座にここに表示されます
    st.session_state.sku_db = st.data_editor(st.session_state.sku_db, num_rows="dynamic", use_container_width=True, key="sku_ed")

# --- タブ3：各種設定 ---
with tab3:
    ca, cb = st.columns(2)
    with ca:
        st.subheader("👥 カメラマン設定")
        st.session_state.m_df = st.data_editor(st.session_state.m_df, hide_index=True, key="m_ed")
    with cb:
        st.subheader("🏷️ ブランド・単価設定")
        st.session_state.b_df = st.data_editor(st.session_state.b_df, hide_index=True, key="b_ed")

import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="rubyohoto 収支管理", layout="wide")

# --- 1. データの初期化 (session_state) ---
if 'm_df' not in st.session_state:
    st.session_state.m_df = pd.DataFrame([
        {"氏名": "森さん", "日給": 15000, "目標SKU": 15},
        {"氏名": "宇田さん", "日給": 14300, "目標SKU": 14},
        {"氏名": "三沖さん", "日給": 13000, "目標SKU": 12},
        {"氏名": "野澤さん", "日給": 13000, "目標SKU": 12}
    ])

# 18.44.08の通り「カット単価」として設定
if 'b_df' not in st.session_state:
    st.session_state.b_df = pd.DataFrame([
        {"ブランド名": "VW(モデル)", "カット単価": 2150},
        {"ブランド名": "VW(トルソー)", "カット単価": 3500},
        {"ブランド名": "MKOL", "カット単価": 1500},
        {"ブランド名": "DS", "カット単価": 700},
        {"ブランド名": "VAL", "カット単価": 1100},
        {"ブランド名": "BP", "カット単価": 600},
        {"ブランド名": "HK", "カット単価": 700},
        {"ブランド名": "MJ", "カット単価": 1850}
    ])

# シフト設定 (タイポ「氏 name」を「氏名」に修正しました)
if 'shift_df' not in st.session_state:
    st.session_state.shift_df = pd.DataFrame([
        {"氏名": "森さん", "期間": "2026/05 第1期 (1-20日)", "シフト日数": 6, "交通費": 816},
        {"氏名": "宇田さん", "期間": "2026/05 第1期 (1-20日)", "シフト日数": 4, "交通費": 0},
        {"氏名": "三沖さん", "期間": "2026/05 第1期 (1-20日)", "シフト日数": 3, "交通費": 0},
        {"氏名": "野澤さん", "期間": "2026/05 第1期 (1-20日)", "シフト日数": 1, "交通費": 0}
    ])

if 'sku_db' not in st.session_state:
    st.session_state.sku_db = pd.DataFrame(columns=["日付", "氏名", "ブランド", "実績SKU", "総カット数"])

st.title("📸 rubyohoto 撮影収支管理")

tab1, tab2, tab3 = st.tabs(["📉 収支分析", "📝 実績入力・コスト設定", "⚙️ 各種設定"])

# --- タブ1：収支分析 ---
with tab1:
    st.header("📊 収支分析レポート")
    
    if not st.session_state.sku_db.empty:
        # 計算：売上 = 総カット数 × カット単価
        calc_df = pd.merge(st.session_state.sku_db, st.session_state.b_df, left_on="ブランド", right_on="ブランド名", how="left")
        calc_df['売上金額'] = calc_df['総カット数'] * calc_df['カット単価'].fillna(0)
        
        summary = calc_df.groupby('氏名').agg({'実績SKU': 'sum', '総カット数': 'sum', '売上金額': 'sum'}).reset_index()
        
        # マスタ・シフト情報を統合
        final = pd.merge(st.session_state.m_df, summary, on='氏名', how='left').fillna(0)
        final = pd.merge(final, st.session_state.shift_df[['氏名', 'シフト日数', '交通費']], on='氏名', how='left').fillna(0)
        
        final['原価合計'] = (final['日給'] * final['シフト日数']) + final['交通費']
        final['利益'] = final['売上金額'] - final['原価合計']

        c1, c2, c3 = st.columns(3)
        c1.metric("総売上", f"¥{int(final['売上金額'].sum()):,}")
        c2.metric("総原価", f"¥{int(final['原価合計'].sum()):,}")
        c3.metric("合計利益", f"¥{int(final['利益'].sum()):,}")

        st.write("---")
        st.subheader("💰 カメラマン別 粗利益")
        # グラフを表示
        st.bar_chart(final.set_index('氏名')['利益'])

        st.subheader("📋 詳細データ")
        disp_df = final[['氏名', '実績SKU', '総カット数', '売上金額', '利益']].rename(columns={'売上金額':'売上'})
        st.dataframe(disp_df.style.format({"売上": "¥{:,.0f}", "利益": "¥{:,.0f}"}), use_container_width=True, hide_index=True)
    else:
        st.info("データがありません。「実績入力」タブから入力してください。")

# --- タブ2：実績入力・コスト設定 ---
with tab2:
    st.subheader("❶ シフト・コスト設定")
    st.session_state.shift_df = st.data_editor(st.session_state.shift_df, hide_index=True, key="sh_ed_v2")
    
    st.divider()
    
    st.subheader("❷ 実績入力")
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
        in_date = col1.date_input("撮影日", datetime.date.today())
        in_name = col2.selectbox("カメラマン", st.session_state.m_df["氏名"].tolist())
        in_brand = col3.selectbox("ブランド", st.session_state.b_df["ブランド名"].tolist())
        in_sku = col4.number_input("SKU数", min_value=0, step=1)
        in_cut = col5.number_input("総カット数", min_value=0, step=1)
        
        if st.button("実績を追加して保存", use_container_width=True):
            new_row = pd.DataFrame([{"日付": str(in_date), "氏名": in_name, "ブランド": in_brand, "実績SKU": in_sku, "総カット数": in_cut}])
            st.session_state.sku_db = pd.concat([st.session_state.sku_db, new_row], ignore_index=True)
            st.rerun()

    st.subheader("▼ 実績リスト（修正・削除可能）")
    # ここに入力データが表示されます
    st.session_state.sku_db = st.data_editor(st.session_state.sku_db, num_rows="dynamic", use_container_width=True, key="sku_ed_v2")

# --- タブ3：各種設定 ---
with tab3:
    ca, cb = st.columns(2)
    with ca:
        st.subheader("👥 カメラマン設定")
        st.session_state.m_df = st.data_editor(st.session_state.m_df, hide_index=True, key="m_ed_v2")
    with cb:
        st.subheader("🏷️ ブランド・カット単価設定")
        st.session_state.b_df = st.data_editor(st.session_state.b_df, hide_index=True, key="b_ed_v2")

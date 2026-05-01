import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF
import io

st.set_page_config(page_title="rubyohoto 収支管理", layout="wide")

# --- 1. データの初期化 ---
if 'm_df' not in st.session_state:
    st.session_state.m_df = pd.DataFrame([
        {"氏名": "森さん", "日給": 15000, "目標SKU": 15},
        {"氏名": "宇田さん", "日給": 14300, "目標SKU": 14},
        {"氏名": "三沖さん", "日給": 13000, "目標SKU": 12},
        {"氏名": "野澤さん", "日給": 13000, "目標SKU": 12}
    ])

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

if 'shift_df' not in st.session_state:
    st.session_state.shift_df = pd.DataFrame([
        {"氏名": "森さん", "期間": "2026/05 第1期", "シフト日数": 6, "調整時間": 0.0, "交通費": 816},
        {"氏名": "宇田さん", "期間": "2026/05 第1期", "シフト日数": 4, "調整時間": 0.0, "交通費": 0},
        {"氏名": "三沖さん", "期間": "2026/05 第1期", "シフト日数": 3, "調整時間": 0.0, "交通費": 0},
        {"氏名": "野澤さん", "期間": "2026/05 第1期", "シフト日数": 1, "調整時間": 0.0, "交通費": 0}
    ])

if 'sku_db' not in st.session_state:
    st.session_state.sku_db = pd.DataFrame(columns=["日付", "氏名", "ブランド", "実績SKU", "総カット数"])

# --- 画面構成 ---
st.title("📸 rubyohoto 撮影収支管理")

tab1, tab2, tab3 = st.tabs(["📉 収支・時間集計", "📝 実績入力・コスト設定", "⚙️ 各種設定"])

# --- タブ1：収支・時間集計 ---
with tab1:
    st.header("📊 総合レポート")
    
    # 売上計算
    calc_df = pd.merge(st.session_state.sku_db, st.session_state.b_df, left_on="ブランド", right_on="ブランド名", how="left")
    calc_df['売上金額'] = calc_df['総カット数'] * calc_df['カット単価'].fillna(0)
    summary = calc_df.groupby('氏名').agg({'実績SKU': 'sum', '総カット数': 'sum', '売上金額': 'sum'}).reset_index()
    
    # 統合
    final = pd.merge(st.session_state.m_df, summary, on='氏名', how='left').fillna(0)
    final = pd.merge(final, st.session_state.shift_df[['氏名', 'シフト日数', '調整時間', '交通費']], on='氏名', how='left').fillna(0)
    final['原価合計'] = (final['日給'] * final['シフト日数']) + final['交通費']
    final['利益'] = final['売上金額'] - final['原価合計']

    # ★ お待たせしました！合計調整時間の計算と表示
    total_adj = st.session_state.shift_df['調整時間'].sum()
    total_shifts = st.session_state.shift_df['シフト日数'].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("総売上", f"¥{int(final['売上金額'].sum()):,}")
    m2.metric("合計利益", f"¥{int(final['利益'].sum()):,}")
    m3.metric("合計シフト", f"{total_shifts}日")
    # deltaを使ってプラスマイナスを強調表示
    m4.metric("合計調整時間", f"{total_adj:+.1f}h", delta=total_adj, delta_color="normal")

    st.write("---")
    c_left, c_right = st.columns(2)
    with c_left:
        st.write("💰 カメラマン別 利益")
        st.bar_chart(final.set_index('氏名')['利益'])
    with c_right:
        st.write("⏳ カメラマン別 調整時間 (+/-)")
        st.bar_chart(final.set_index('氏名')['調整時間'])

    st.subheader("📋 詳細データテーブル")
    # 調整時間もテーブルにしっかり表示
    disp_df = final[['氏名', '実績SKU', '総カット数', 'シフト日数', '調整時間', '売上金額', '利益']].rename(columns={'売上金額':'売上'})
    st.dataframe(disp_df.style.format({"売上": "¥{:,.0f}", "利益": "¥{:,.0f}", "調整時間": "{:+.1f}h"}), use_container_width=True, hide_index=True)

# --- タブ2：実績・コスト設定 ---
with tab2:
    st.subheader("❶ シフト・コスト設定 (調整時間・交通費)")
    # ここに入力した +/- が即座にタブ1の「合計調整時間」に反映されます
    st.session_state.shift_df = st.data_editor(st.session_state.shift_df, hide_index=True, key="shift_v7")
    
    st.divider()
    st.subheader("❷ 撮影実績入力")
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
        i_date = col1.date_input("撮影日")
        i_name = col2.selectbox("カメラマン", st.session_state.m_df["氏名"].tolist())
        i_brand = col3.selectbox("ブランド", st.session_state.b_df["ブランド名"].tolist())
        i_sku = col4.number_input("SKU数", min_value=0)
        i_cut = col5.number_input("総カット数", min_value=0)
        if st.button("実績を追加保存", use_container_width=True):
            new = pd.DataFrame([{"日付": str(i_date), "氏名": i_name, "ブランド": i_brand, "実績SKU": i_sku, "総カット数": i_cut}])
            st.session_state.sku_db = pd.concat([st.session_state.sku_db, new], ignore_index=True)
            st.rerun()

    st.write("▼ 実績リスト")
    st.session_state.sku_db = st.data_editor(st.session_state.sku_db, num_rows="dynamic", use_container_width=True, key="sku_v7")
    
    # CSV保存
    csv = st.session_state.sku_db.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📩 データCSV保存", csv, f"shooting_backup.csv", "text/csv")

# --- タブ3：設定 ---
with tab3:
    ca, cb = st.columns(2)
    ca.subheader("👥 カメラマン設定")
    st.session_state.m_df = st.data_editor(st.session_state.m_df, hide_index=True, key="m_v7")
    cb.subheader("🏷️ ブランド単価設定")
    st.session_state.b_df = st.data_editor(st.session_state.b_df, hide_index=True, key="b_v7")

import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF
import io

# ページ設定
st.set_page_config(page_title="rubyohoto 撮影収支", layout="wide")

# --- 1. データの初期化 (session_state) ---
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

# --- PDF作成ロジック ---
def create_pdf(df, sales, cost, profit, adj_time):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "rubyohoto Profit & Time Report", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Total Adj Time: {adj_time:+.1f} h", ln=True)
    pdf.cell(0, 10, f"Total Sales: {int(sales):,} JPY / Total Profit: {int(profit):,} JPY", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 10, "Name", 1); pdf.cell(20, 10, "SKU", 1); pdf.cell(25, 10, "AdjT", 1)
    pdf.cell(35, 10, "Sales", 1); pdf.cell(35, 10, "Profit", 1); pdf.ln()
    for _, row in df.iterrows():
        pdf.cell(35, 10, str(row['氏名']), 1); pdf.cell(20, 10, str(int(row['実績SKU'])), 1)
        pdf.cell(25, 10, f"{row['調整時間']:+.1f}", 1)
        pdf.cell(35, 10, f"{int(row['売上']):,}", 1); pdf.cell(35, 10, f"{int(row['利益']):,}", 1); pdf.ln()
    return pdf.output()

# --- 画面構成 ---
st.title("📸 rubyohoto 撮影収支管理（完結版）")

tab1, tab2, tab3 = st.tabs(["📉 収支・時間集計", "📝 実績入力・データ保存", "⚙️ 各種設定"])

# --- タブ1：収支・時間集計 ---
with tab1:
    # リアルタイム計算
    calc_df = pd.merge(st.session_state.sku_db, st.session_state.b_df, left_on="ブランド", right_on="ブランド名", how="left")
    calc_df['売上金額'] = calc_df['総カット数'] * calc_df['カット単価'].fillna(0)
    summary = calc_df.groupby('氏名').agg({'実績SKU': 'sum', '総カット数': 'sum', '売上金額': 'sum'}).reset_index()
    
    final = pd.merge(st.session_state.m_df, summary, on='氏名', how='left').fillna(0)
    final = pd.merge(final, st.session_state.shift_df[['氏名', 'シフト日数', '調整時間', '交通費']], on='氏名', how='left').fillna(0)
    final['原価合計'] = (final['日給'] * final['シフト日数']) + final['交通費']
    final['利益'] = final['売上金額'] - final['原価合計']

    # ★ 合計調整時間を算出
    total_adj = st.session_state.shift_df['調整時間'].sum()
    total_shifts = st.session_state.shift_df['シフト日数'].sum()

    # メトリクス表示
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("総売上", f"¥{int(final['売上金額'].sum()):,}")
    m2.metric("合計利益", f"¥{int(final['利益'].sum()):,}")
    m3.metric("合計シフト", f"{total_shifts}日")
    # ここに合計時間を表示。色（delta）でもプラスマイナスを表現
    m4.metric("合計調整時間", f"{total_adj:+.1f}h", delta=total_adj, delta_color="normal")

    st.write("---")
    col_l, col_r = st.columns(2)
    with col_l:
        st.write("💰 カメラマン別利益")
        st.bar_chart(final.set_index('氏名')['利益'])
    with col_r:
        st.write("⏳ 調整時間状況 (+/-)")
        st.bar_chart(final.set_index('氏名')['調整時間'])

    st.subheader("📋 詳細レポートテーブル")
    disp_df = final[['氏名', '実績SKU', '総カット数', 'シフト日数', '調整時間', '売上金額', '利益']].rename(columns={'売上金額':'売上'})
    st.dataframe(disp_df.style.format({"売上": "¥{:,.0f}", "利益": "¥{:,.0f}", "調整時間": "{:+.1f}h"}), use_container_width=True, hide_index=True)

    if st.button("📄 PDFレポートを生成・ダウンロード"):
        pdf_bytes = create_pdf(disp_df, final['売上金額'].sum(), final['原価合計'].sum(), final['利益'].sum(), total_shifts, total_adj)
        st.download_button("📥 PDF保存", pdf_bytes, f"shooting_report_{datetime.date.today()}.pdf", "application/pdf")

# --- タブ2：実績入力・データ保存 ---
with tab2:
    st.subheader("📥 過去データの復元 (CSV)")
    up_csv = st.file_uploader("保存したCSVファイルをアップロードしてください", type="csv")
    if up_csv:
        st.session_state.sku_db = pd.read_csv(up_csv)
        st.success("データを復元しました！")

    st.divider()
    st.subheader("❶ シフト・調整時間・交通費の設定")
    # ここで調整時間に -2 などを入れると、タブ1の合計が即座に変わります
    st.session_state.shift_df = st.data_editor(st.session_state.shift_df, hide_index=True, key="sh_final_v1")
    
    st.divider()
    st.subheader("❷ 本日の撮影実績入力")
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
        i_date = c1.date_input("撮影日")
        i_name = c2.selectbox("カメラマン", st.session_state.m_df["氏名"].tolist())
        i_brand = c3.selectbox("ブランド", st.session_state.b_df["ブランド名"].tolist())
        i_sku = c4.number_input("SKU数", min_value=0)
        i_cut = c5.number_input("総カット数", min_value=0)
        if st.button("実績データを追加保存", use_container_width=True):
            new_data = pd.DataFrame([{"日付": str(i_date), "氏名": i_name, "ブランド": i_brand, "実績SKU": i_sku, "総カット数": i_cut}])
            st.session_state.sku_db = pd.concat([st.session_state.sku_db, new_data], ignore_index=True)
            st.rerun()

    st.subheader("▼ 実績データリスト (編集・削除)")
    st.session_state.sku_db = st.data_editor(st.session_state.sku_db, num_rows="dynamic", use_container_width=True, key="sku_final_v1")

    st.divider()
    st.subheader("📤 データのバックアップ保存")
    st.write("ブラウザを閉じるとデータが消えるため、必ず作業後にダウンロードしてください。")
    csv_file = st.session_state.sku_db.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📩 今日のデータをCSVで保存", csv_file, f"shooting_data_{datetime.date.today()}.csv", "text/csv")

# --- タブ3：設定 ---
with tab3:
    ca, cb = st.columns(2)
    with ca:
        st.subheader("👥 カメラマン基本設定")
        st.session_state.m_df = st.data_editor(st.session_state.m_df, hide_index=True, key="m_master_final")
    with cb:
        st.subheader("🏷️ ブランド別カット単価")
        st.session_state.b_df = st.data_editor(st.session_state.b_df, hide_index=True, key="b_master_final")

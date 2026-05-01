import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF
import io

st.set_page_config(page_title="rubyohoto 収支管理", layout="wide")

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
        {"氏名": "森さん", "期間": "2026/05 第1期", "シフト日数": 6, "調整時間": 0, "交通費": 816},
        {"氏名": "宇田さん", "期間": "2026/05 第1期", "シフト日数": 4, "調整時間": 0, "交通費": 0},
        {"氏名": "三沖さん", "期間": "2026/05 第1期", "シフト日数": 3, "調整時間": 0, "交通費": 0},
        {"氏名": "野澤さん", "期間": "2026/05 第1期", "シフト日数": 1, "調整時間": 0, "交通費": 0}
    ])

if 'sku_db' not in st.session_state:
    st.session_state.sku_db = pd.DataFrame(columns=["日付", "氏名", "ブランド", "実績SKU", "総カット数"])

# --- PDF作成関数 ---
def create_pdf(df, total_sales, total_cost, total_profit):
    pdf = FPDF()
    pdf.add_page()
    # 日本語フォント設定が環境により難しいため、標準フォントで構成
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "rubyohoto Shooting Profit Report", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Date: {datetime.date.today()}", ln=True)
    pdf.cell(0, 10, f"Total Sales: {int(total_sales):,} JPY", ln=True)
    pdf.cell(0, 10, f"Total Cost: {int(total_cost):,} JPY", ln=True)
    pdf.cell(0, 10, f"Total Profit: {int(total_profit):,} JPY", ln=True)
    pdf.ln(10)
    
    # テーブルヘッダー
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(30, 10, "Name", 1)
    pdf.cell(30, 10, "SKU", 1)
    pdf.cell(30, 10, "Cuts", 1)
    pdf.cell(40, 10, "Sales", 1)
    pdf.cell(40, 10, "Profit", 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 10)
    for index, row in df.iterrows():
        pdf.cell(30, 10, str(row['氏名']), 1)
        pdf.cell(30, 10, str(int(row['実績SKU'])), 1)
        pdf.cell(30, 10, str(int(row['総カット数'])), 1)
        pdf.cell(40, 10, f"{int(row['売上']):,}", 1)
        pdf.cell(40, 10, f"{int(row['利益']):,}", 1)
        pdf.ln()
    
    return pdf.output()

# --- アプリ画面 ---
st.title("📸 rubyohoto 撮影収支管理")

tab1, tab2, tab3 = st.tabs(["📉 収支分析・PDF出力", "📝 実績入力・データ保存", "⚙️ 各種設定"])

# --- タブ1：収支分析 ---
with tab1:
    st.header("📊 収支レポート")
    calc_df = pd.merge(st.session_state.sku_db, st.session_state.b_df, left_on="ブランド", right_on="ブランド名", how="left")
    calc_df['売上金額'] = calc_df['総カット数'] * calc_df['カット単価'].fillna(0)
    summary = calc_df.groupby('氏名').agg({'実績SKU': 'sum', '総カット数': 'sum', '売上金額': 'sum'}).reset_index()
    
    final = pd.merge(st.session_state.m_df, summary, on='氏名', how='left').fillna(0)
    final = pd.merge(final, st.session_state.shift_df[['氏名', 'シフト日数', '調整時間', '交通費']], on='氏名', how='left').fillna(0)
    
    final['原価合計'] = (final['日給'] * final['シフト日数']) + final['交通費']
    final['利益'] = final['売上金額'] - final['原価合計']

    c1, c2, c3 = st.columns(3)
    c1.metric("総売上", f"¥{int(final['売上金額'].sum()):,}")
    c2.metric("総原価", f"¥{int(final['原価合計'].sum()):,}")
    c3.metric("合計利益", f"¥{int(final['利益'].sum()):,}")

    st.bar_chart(final.set_index('氏名')['利益'])
    
    disp_df = final[['氏名', '実績SKU', '総カット数', '売上金額', '利益']].rename(columns={'売上金額':'売上'})
    st.dataframe(disp_df.style.format({"売上": "¥{:,.0f}", "利益": "¥{:,.0f}"}), use_container_width=True, hide_index=True)

    st.divider()
    # PDF出力ボタン
    if st.button("📄 レポートをPDFとして書き出す"):
        pdf_bytes = create_pdf(disp_df, final['売上金額'].sum(), final['原価合計'].sum(), final['利益'].sum())
        st.download_button(label="📥 PDFをダウンロード", data=pdf_bytes, file_name=f"report_{datetime.date.today()}.pdf", mime="application/pdf")

# --- タブ2：入力・保存 ---
with tab2:
    st.subheader("💾 データの復元 (CSVアップロード)")
    up_file = st.file_uploader("保存したCSVを選択", type="csv")
    if up_file:
        st.session_state.sku_db = pd.read_csv(up_file)
    
    st.divider()
    st.subheader("❶ シフト・コスト設定（調整時間あり）")
    st.session_state.shift_df = st.data_editor(st.session_state.shift_df, hide_index=True)
    
    st.divider()
    st.subheader("❷ 実績入力")
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
        in_date = col1.date_input("撮影日")
        in_name = col2.selectbox("カメラマン", st.session_state.m_df["氏名"].tolist())
        in_brand = col3.selectbox("ブランド", st.session_state.b_df["ブランド名"].tolist())
        in_sku = col4.number_input("SKU数", min_value=0)
        in_cut = col5.number_input("総カット数", min_value=0)
        if st.button("実績を追加"):
            new = pd.DataFrame([{"日付": str(in_date), "氏名": in_name, "ブランド": in_brand, "実績SKU": in_sku, "総カット数": in_cut}])
            st.session_state.sku_db = pd.concat([st.session_state.sku_db, new], ignore_index=True)
            st.rerun()

    st.subheader("▼ 実績リスト")
    st.session_state.sku_db = st.data_editor(st.session_state.sku_db, num_rows="dynamic", use_container_width=True)

    st.divider()
    csv = st.session_state.sku_db.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📩 データをCSVで保存", csv, f"data_{datetime.date.today()}.csv", "text/csv")

# --- タブ3：設定 ---
with tab3:
    ca, cb = st.columns(2)
    with ca:
        st.subheader("👥 カメラマン設定")
        st.session_state.m_df = st.data_editor(st.session_state.m_df, hide_index=True)
    with cb:
        st.subheader("🏷️ ブランド単価設定")
        st.session_state.b_df = st.data_editor(st.session_state.b_df, hide_index=True)

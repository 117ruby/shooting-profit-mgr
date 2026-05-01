import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF
import io

# ページ設定
st.set_page_config(page_title="rubyohoto 収支管理", layout="wide")

# --- 1. データの初期化 (session_state) ---
# カメラマンマスタ
if 'm_df' not in st.session_state:
    st.session_state.m_df = pd.DataFrame([
        {"氏名": "森さん", "日給": 15000, "目標SKU": 15},
        {"氏名": "宇田さん", "日給": 14300, "目標SKU": 14},
        {"氏名": "三沖さん", "日給": 13000, "目標SKU": 12},
        {"氏名": "野澤さん", "日給": 13000, "目標SKU": 12}
    ])

# ブランド・カット単価設定
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

# シフト・コスト設定 (調整時間あり)
if 'shift_df' not in st.session_state:
    st.session_state.shift_df = pd.DataFrame([
        {"氏名": "森さん", "期間": "2026/05 第1期", "シフト日数": 6, "調整時間": 0, "交通費": 816},
        {"氏名": "宇田さん", "期間": "2026/05 第1期", "シフト日数": 4, "調整時間": 0, "交通費": 0},
        {"氏名": "三沖さん", "期間": "2026/05 第1期", "シフト日数": 3, "調整時間": 0, "交通費": 0},
        {"氏名": "野澤さん", "期間": "2026/05 第1期", "シフト日数": 1, "調整時間": 0, "交通費": 0}
    ])

# 撮影実績データベース
if 'sku_db' not in st.session_state:
    st.session_state.sku_db = pd.DataFrame(columns=["日付", "氏名", "ブランド", "実績SKU", "総カット数"])

# --- PDF作成用クラス (日本語フォント未対応環境のため英語ラベル) ---
def create_pdf(df, total_sales, total_cost, total_profit):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "rubyohoto Profit Report", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Date: {datetime.date.today()}", ln=True)
    pdf.cell(0, 10, f"Total Sales: {int(total_sales):,} JPY", ln=True)
    pdf.cell(0, 10, f"Total Cost: {int(total_cost):,} JPY", ln=True)
    pdf.cell(0, 10, f"Total Profit: {int(total_profit):,} JPY", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 10, "Name", 1)
    pdf.cell(25, 10, "SKU", 1)
    pdf.cell(25, 10, "Cuts", 1)
    pdf.cell(40, 10, "Sales", 1)
    pdf.cell(40, 10, "Profit", 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 10)
    for _, row in df.iterrows():
        pdf.cell(35, 10, str(row['氏名']), 1)
        pdf.cell(25, 10, str(int(row['実績SKU'])), 1)
        pdf.cell(25, 10, str(int(row['総カット数'])), 1)
        pdf.cell(40, 10, f"{int(row['売上']):,}", 1)
        pdf.cell(40, 10, f"{int(row['利益']):,}", 1)
        pdf.ln()
    return pdf.output()

# --- メイン画面 ---
st.title("📸 rubyohoto 撮影収支管理")

tab1, tab2, tab3 = st.tabs(["📉 収支分析", "📝 実績入力・保存", "⚙️ 各種設定"])

# --- タブ1：収支分析 ---
with tab1:
    st.header("📊 収支レポート")
    
    # 計算：売上 = 総カット数 × カット単価
    calc_df = pd.merge(st.session_state.sku_db, st.session_state.b_df, left_on="ブランド", right_on="ブランド名", how="left")
    calc_df['売上金額'] = calc_df['総カット数'] * calc_df['カット単価'].fillna(0)
    
    summary = calc_df.groupby('氏名').agg({'実績SKU': 'sum', '総カット数': 'sum', '売上金額': 'sum'}).reset_index()
    
    # 全データを統合
    final = pd.merge(st.session_state.m_df, summary, on='氏名', how='left').fillna(0)
    final = pd.merge(final, st.session_state.shift_df[['氏名', 'シフト日数', '調整時間', '交通費']], on='氏名', how='left').fillna(0)
    
    # 原価計算：(日給 * シフト日数) + 交通費
    final['原価合計'] = (final['日給'] * final['シフト日数']) + final['交通費']
    final['利益'] = final['売上金額'] - final['原価合計']

    # メトリクス
    c1, c2, c3 = st.columns(3)
    c1.metric("総売上", f"¥{int(final['売上金額'].sum()):,}")
    c2.metric("総原価", f"¥{int(final['原価合計'].sum()):,}")
    c3.metric("合計利益", f"¥{int(final['利益'].sum()):,}")

    st.write("---")
    st.subheader("💰 カメラマン別 利益推移")
    st.bar_chart(final.set_index('氏名')['利益'])

    st.subheader("📋 詳細データテーブル")
    disp_df = final[['氏名', '実績SKU', '総カット数', '売上金額', '利益']].rename(columns={'売上金額':'売上'})
    st.dataframe(disp_df.style.format({"売上": "¥{:,.0f}", "利益": "¥{:,.0f}"}), use_container_width=True, hide_index=True)

    # PDF書き出し
    if st.button("📄 収支レポートをPDFで作成"):
        pdf_out = create_pdf(disp_df, final['売上金額'].sum(), final['原価合計'].sum(), final['利益'].sum())
        st.download_button(label="📥 PDFをダウンロード", data=pdf_out, file_name=f"report_{datetime.date.today()}.pdf", mime="application/pdf")

# --- タブ2：入力・保存 ---
with tab2:
    st.subheader("💾 過去データの読み込み (CSV)")
    up_csv = st.file_uploader("保存済みのCSVをアップロード", type="csv")
    if up_csv:
        st.session_state.sku_db = pd.read_csv(up_csv)
        st.success("データを復元しました。")

    st.divider()
    st.subheader("❶ シフト・コスト設定 (調整時間あり)")
    st.session_state.shift_df = st.data_editor(st.session_state.shift_df, hide_index=True, key="shift_editor_v5")
    
    st.divider()
    st.subheader("❷ 実績入力 (カット単価方式)")
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
        i_date = col1.date_input("撮影日")
        i_name = col2.selectbox("カメラマン", st.session_state.m_df["氏名"].tolist())
        i_brand = col3.selectbox("ブランド", st.session_state.b_df["ブランド名"].tolist())
        i_sku = col4.number_input("SKU数", min_value=0)
        i_cut = col5.number_input("総カット数", min_value=0)
        if st.button("データを追加", use_container_width=True):
            new_row = pd.DataFrame([{"日付": str(i_date), "氏名": i_name, "ブランド": i_brand, "実績SKU": i_sku, "総カット数": i_cut}])
            st.session_state.sku_db = pd.concat([st.session_state.sku_db, new_row], ignore_index=True)
            st.rerun()

    st.subheader("▼ 撮影実績リスト (編集・削除)")
    st.session_state.sku_db = st.data_editor(st.session_state.sku_db, num_rows="dynamic", use_container_width=True, key="sku_editor_v5")

    st.divider()
    st.subheader("📥 データのバックアップ")
    csv_bytes = st.session_state.sku_db.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📩 本日のデータをCSVで保存", csv_bytes, f"shooting_data_{datetime.date.today()}.csv", "text/csv")

# --- タブ3：設定 ---
with tab3:
    ca, cb = st.columns(2)
    with ca:
        st.subheader("👥 カメラマン基本設定")
        st.session_state.m_df = st.data_editor(st.session_state.m_df, hide_index=True, key="m_master_v5")
    with cb:
        st.subheader("🏷️ ブランド・カット単価設定")
        st.session_state.b_df = st.data_editor(st.session_state.b_df, hide_index=True, key="b_master_v5")

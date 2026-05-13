import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF
import io
import math

st.set_page_config(page_title="rubyohoto 撮影収支", layout="wide")

# --- 1. データの初期化 ---
name_order = ["森さん", "宇田さん", "三沖さん", "野澤さん"]

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
        {"ブランド名": "VW(雑貨)", "カット単価": 960},
        {"ブランド名": "MKOL", "カット単価": 1500},
        {"ブランド名": "DS", "カット単価": 700},
        {"ブランド名": "VAL", "カット単価": 1100},
        {"ブランド名": "BP", "カット単価": 600},
        {"ブランド名": "HK", "カット単価": 700},
        {"ブランド名": "MJ", "カット単価": 1850}
    ])

if 'shift_df' not in st.session_state:
    st.session_state.shift_df = pd.DataFrame([
        {"名前": "森さん", "期間": "2026/05 前半", "シフト日数": 6, "合計時間": 48.0, "調整時間": 0.0, "交通費": 816},
        {"名前": "宇田さん", "期間": "2026/05 前半", "シフト日数": 4, "合計時間": 32.0, "調整時間": 0.0, "交通費": 0},
        {"名前": "三沖さん", "期間": "2026/05 前半", "シフト日数": 3, "合計時間": 24.0, "調整時間": 0.0, "交通費": 0},
        {"名前": "野澤さん", "期間": "2026/05 前半", "シフト日数": 1, "合計時間": 8.0, "調整時間": 0.0, "交通費": 0}
    ])

if 'sku_db' not in st.session_state:
    st.session_state.sku_db = pd.DataFrame(columns=["期間", "日付", "氏名", "ブランド", "実績SKU", "総カット数"])

# --- 2. データ集計ロジック ---
def clean_all_data():
    for col in ['シフト日数', '調整時間', '交通費']:
        st.session_state.shift_df[col] = pd.to_numeric(st.session_state.shift_df[col], errors='coerce').fillna(0)
    st.session_state.shift_df['合計時間'] = (st.session_state.shift_df['シフト日数'] * 8.0) + st.session_state.shift_df['調整時間']
    if not st.session_state.sku_db.empty:
        for col in ['実績SKU', '総カット数']:
            st.session_state.sku_db[col] = pd.to_numeric(st.session_state.sku_db[col], errors='coerce').fillna(0).astype(int)

# --- 3. PDF作成 ---
def create_pdf(period_name, df, total_sales, total_cost, company_profit, adj_time):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18); pdf.set_text_color(0, 104, 201)
    pdf.cell(0, 10, f"rubyohoto PERFORMANCE ({period_name})", ln=True, align='C'); pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(0, 0, 0); pdf.set_fill_color(240, 242, 246)
    pdf.cell(0, 10, f"  [COMPANY] Sales: JPY {int(total_sales):,}  /  Cost: JPY {int(total_cost):,}", ln=True, fill=True)
    pdf.set_font("Helvetica", "B", 12)
    if company_profit < 0: pdf.set_text_color(255, 75, 75)
    pdf.cell(0, 10, f"COMPANY NET PROFIT: {int(company_profit):+,} JPY", ln=True, align='R'); pdf.ln(5)
    pdf.set_font("Helvetica", "B", 8); pdf.set_text_color(255, 255, 255); pdf.set_fill_color(0, 104, 201)
    pdf.cell(25, 10, "Name", 1, 0, 'C', True); pdf.cell(25, 10, "SKU(Act/Tgt)", 1, 0, 'C', True)
    pdf.cell(15, 10, "Diff", 1, 0, 'C', True); pdf.cell(25, 10, "L-Cost", 1, 0, 'C', True)
    pdf.cell(35, 10, "Perf. P/L", 1, 0, 'C', True); pdf.cell(60, 10, "Status", 1, 1, 'C', True)
    pdf.set_font("Helvetica", "", 10); pdf.set_text_color(0, 0, 0)
    for _, row in df.iterrows():
        pdf.cell(25, 10, row['氏名'], 1, 0, 'C')
        pdf.cell(25, 10, f"{int(row['実績SKU'])} / {int(row['目標SKU合計'])}", 1, 0, 'C')
        pdf.cell(15, 10, f"{int(row['SKU差分']):+}", 1, 0, 'C')
        pdf.cell(25, 10, f"{int(row['人件費']):,}", 1, 0, 'R')
        rp = int(row['稼働損益'])
        if rp < 0: pdf.set_text_color(255, 75, 75)
        pdf.cell(35, 10, f"{rp:+,}", 1, 0, 'R'); pdf.set_text_color(0, 0, 0)
        status_txt = f"Missing {abs(int(row['SKU差分']))} SKUs" if row['SKU差分'] < 0 else "Target Cleared!"
        pdf.cell(60, 10, status_txt, 1, 1, 'C')
    output_raw = pdf.output(dest='S')
    return bytes(output_raw) if not isinstance(output_raw, str) else output_raw.encode('latin-1')

clean_all_data()

# --- 4. サイドバー ---
st.sidebar.title("📅 対象期間の選択")
sel_year = st.sidebar.number_input("年", min_value=2024, max_value=2030, value=2026)
sel_month = st.sidebar.selectbox("月", [f"{i:02d}" for i in range(1, 13)], index=4)
sel_half = st.sidebar.radio("期間", ["前半 (1日〜15日)", "後半 (16日〜月末)"])
selected_period = f"{sel_year}/{sel_month} {'前半' if '前半' in sel_half else '後半'}"
st.sidebar.success(f"現在 **【 {selected_period} 】** 選択中")

# --- 5. メイン画面 ---
st.title("📸 rubyohoto 撮影収支管理")
tab1, tab2, tab3 = st.tabs(["📉 収支・時間集計", "📝 実績入力・コスト設定", "⚙️ 各種設定"])

with tab1:
    st.header(f"📊 総合レポート ({selected_period})")
    f_shift = st.session_state.shift_df[st.session_state.shift_df['期間'] == selected_period]
    f_sku = st.session_state.sku_db[st.session_state.sku_db['期間'] == selected_period]
    s_merge = f_shift.rename(columns={'名前': '氏名'})
    shift_summary = s_merge.groupby('氏名').agg({'シフト日数': 'sum', '合計時間': 'sum', '調整時間': 'sum', '交通費': 'sum'}).reset_index()
    if not f_sku.empty:
        calc_df = pd.merge(f_sku, st.session_state.b_df, left_on="ブランド", right_on="ブランド名", how="left")
        calc_df['売上金額'] = calc_df['総カット数'] * calc_df['カット単価'].fillna(0)
        sku_summary = calc_df.groupby('氏名').agg({'実績SKU': 'sum', '総カット数': 'sum', '売上金額': 'sum'}).reset_index()
    else:
        sku_summary = pd.DataFrame(columns=['氏名', '実績SKU', '総カット数', '売上金額'])
    
    final = pd.merge(st.session_state.m_df, sku_summary, on='氏名', how='left').fillna(0)
    final = pd.merge(final, shift_summary, on='氏名', how='left').fillna(0)
    final['人件費'] = (final['日給'] * final['シフト日数']) + final['交通費']
    final['会社利益'] = final['売上金額'] - final['人件費']
    final['目標SKU合計'] = final['目標SKU'] * final['シフト日数']
    final['SKU差分'] = final['実績SKU'] - final['目標SKU合計']
    # ★ 1SKU単価（ノルマ単価）の可視化
    final['ノルマ単価'] = final.apply(lambda row: row['日給'] / row['目標SKU'] if row['目標SKU'] > 0 else 0, axis=1)
    final['稼働損益'] = (final['SKU差分'] * final['ノルマ単価']) - final['交通費']
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("総売上 (請求ベース)", f"¥{int(final['売上金額'].sum()):,}")
    m2.metric("総人件費 (支出)", f"¥{int(final['人件費'].sum()):,}")
    m3.metric("会社粗利", f"{int(final['会社利益'].sum()):+,}")
    m4.metric("稼働損益(チーム計)", f"{int(final['稼働損益'].sum()):+,}")

    st.divider(); st.subheader("📊 個人の稼働損益（実力評価）")
    chart_df = final[final['目標SKU合計'] > 0][['氏名', '稼働損益', 'SKU差分']].copy()
    if not chart_df.empty:
        chart_df['色'] = chart_df['SKU差分'].apply(lambda x: '#0068C9' if x >= 0 else '#FF4B4B')
        st.bar_chart(chart_df, x='氏名', y='稼働損益', color='色')

    st.subheader("📋 詳細レポート")
    # ノルマ単価を列に加える
    disp_df = final[['氏名', 'ノルマ単価', '稼働損益', '実績SKU', '目標SKU合計', 'SKU差分', '人件費', '売上金額']].rename(columns={'売上金額':'参考売上'})
    st.dataframe(disp_df.style.format({
        "参考売上": "¥{:,.0f}", "人件費": "¥{:,.0f}", "稼働損益": lambda x: f"{int(x):+,}", 
        "ノルマ単価": "¥{:,.0f}", "実績SKU": "{:.0f}着", "目標SKU合計": "{:.0f}着", "SKU差分": "{:+.0f}着"
    }), use_container_width=True, hide_index=True)

    if st.button("📄 レポートPDF保存"):
        pdf_data = create_pdf(selected_period, final, final['売上金額'].sum(), final['人件費'].sum(), final['会社利益'].sum(), shift_summary['調整時間'].sum())
        st.download_button(label="📥 ダウンロード", data=pdf_data, file_name=f"report_{selected_period}.pdf", mime="application/pdf")

with tab2:
    st.subheader(f"❶ シフト・コスト設定 ({selected_period})")
    f_shift = st.session_state.shift_df[st.session_state.shift_df['期間'] == selected_period]
    if f_shift.empty:
        f_shift = pd.DataFrame([{"名前": n, "期間": selected_period, "シフト日数": 0, "合計時間": 0.0, "調整時間": 0.0, "交通費": 0} for n in name_order])
        st.session_state.shift_df = pd.concat([st.session_state.shift_df, f_shift], ignore_index=True)
    f_shift['名前'] = pd.Categorical(f_shift['名前'], categories=name_order, ordered=True)
    edited_shift = st.data_editor(f_shift.sort_values('名前'), column_order=["名前", "シフト日数", "合計時間", "調整時間", "交通費"], disabled=["合計時間"], hide_index=True, key="sh_v34", use_container_width=True)
    if not edited_shift.equals(f_shift.sort_values('名前')):
        edited_shift['期間'] = selected_period
        st.session_state.shift_df = pd.concat([st.session_state.shift_df[st.session_state.shift_df['期間'] != selected_period], edited_shift], ignore_index=True)
        clean_all_data(); st.rerun()
    st.divider(); st.subheader(f"❷ 撮影実績入力 ({selected_period})")
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
        i_date = c1.date_input("撮影日"); i_name = c2.selectbox("カメラマン", name_order); in_brand = c3.selectbox("ブランド", st.session_state.b_df["ブランド名"].tolist()); i_sku = c4.number_input("実績SKU", min_value=0, step=1); i_cut = c5.number_input("総カット数", min_value=0, step=1)
        if st.button("実績を追加保存", use_container_width=True):
            new = pd.DataFrame([{"期間": selected_period, "日付": str(i_date), "氏名": i_name, "ブランド": in_brand, "実績SKU": int(i_sku), "総カット数": int(i_cut)}])
            st.session_state.sku_db = pd.concat([st.session_state.sku_db, new], ignore_index=True); clean_all_data(); st.rerun()
    f_sku = st.session_state.sku_db[st.session_state.sku_db['期間'] == selected_period]
    edited_sku = st.data_editor(f_sku, num_rows="dynamic", use_container_width=True, key="sku_v34")
    if not edited_sku.equals(f_sku):
        edited_sku['期間'] = selected_period
        st.session_state.sku_db = pd.concat([st.session_state.sku_db[st.session_state.sku_db['期間'] != selected_period], edited_sku], ignore_index=True)
        clean_all_data(); st.rerun()

with tab3:
    st.header("💾 バックアップ・各種設定")
    ca, cb = st.columns(2)
    with ca:
        st.subheader("👥 氏名・日給設定")
        st.session_state.m_df = st.data_editor(st.session_state.m_df, hide_index=True, key="m_v34")
        # ★ ここに「1SKU単価（ノルマ単価）」の早見表を追加
        st.write("▼ 現在のノルマ単価（確認用）")
        calc_m = st.session_state.m_df.copy()
        calc_m['ノルマ単価'] = calc_m.apply(lambda r: f"¥{int(r['日給']/r['目標SKU']):,}/着" if r['目標SKU']>0 else "未設定", axis=1)
        st.dataframe(calc_m[['氏名', 'ノルマ単価']], hide_index=True, use_container_width=True)
    with cb:
        st.subheader("🏷️ ブランド・単価設定")
        st.session_state.b_df = st.data_editor(st.session_state.b_df, hide_index=True, key="b_v34")
    st.divider()
    st.download_button(label="📥 全データをCSVで保存", data=st.session_state.sku_db.to_csv(index=False).encode('utf-8-sig'), file_name="rubyohoto_backup.csv", mime='text/csv')

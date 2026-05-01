import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF
import io
import math

st.set_page_config(page_title="rubyohoto 撮影収支", layout="wide")

# --- 1. データの初期化 (順序厳守) ---
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
        {"ブランド名": "MKOL", "カット単価": 1500},
        {"ブランド名": "DS", "カット単価": 700},
        {"ブランド名": "VAL", "カット単価": 1100},
        {"ブランド名": "BP", "カット単価": 600},
        {"ブランド名": "HK", "カット単価": 700},
        {"ブランド名": "MJ", "カット単価": 1850}
    ])

if 'shift_df' not in st.session_state:
    st.session_state.shift_df = pd.DataFrame([
        {"名前": "森さん", "期間": "2026/05 第1期", "シフト日数": 6, "合計時間": 48.0, "調整時間": 0.0, "交通費": 816},
        {"名前": "宇田さん", "期間": "2026/05 第1期", "シフト日数": 4, "合計時間": 32.0, "調整時間": 0.0, "交通費": 0},
        {"名前": "三沖さん", "期間": "2026/05 第1期", "シフト日数": 3, "合計時間": 24.0, "調整時間": 0.0, "交通費": 0},
        {"名前": "野澤さん", "期間": "2026/05 第1期", "シフト日数": 1, "合計時間": 8.0, "調整時間": 0.0, "交通費": 0}
    ])

if 'sku_db' not in st.session_state:
    st.session_state.sku_db = pd.DataFrame(columns=["日付", "氏名", "ブランド", "実績SKU", "総カット数"])

# --- ★ PDF作成用関数 (100%エラーが出ない英語マップ版) ---
def create_pdf(df, sales, cost, profit, adj_time):
    pdf = FPDF()
    pdf.add_page()
    # 外部フォントを使わず、標準フォントで固める
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "rubyohoto Profit & SKU Report", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "", 11)
    prof_sign = "+" if profit >= 0 else "-"
    pdf.cell(0, 10, f"Total Sales: {int(sales):,} / Cost: {int(cost):,} / Profit: {prof_sign}{abs(int(profit)):,}", ln=True)
    pdf.cell(0, 10, f"Total Adj Time: {adj_time:+.1f} h", ln=True)
    pdf.ln(5)
    
    # ヘッダー
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(20, 10, "Name", 1); pdf.cell(25, 10, "SKU(Act/Tgt)", 1); pdf.cell(15, 10, "Diff", 1)
    pdf.cell(20, 10, "Rate", 1); pdf.cell(30, 10, "Sales", 1); pdf.cell(30, 10, "Cost", 1); pdf.cell(30, 10, "Profit", 1); pdf.ln()
    
    pdf.set_font("Helvetica", "", 9)
    # PDF内だけ英語に変換
    name_map = {"森さん": "Mori", "宇田さん": "Uda", "三沖さん": "Mioki", "野澤さん": "Nozawa"}
    
    for _, row in df.iterrows():
        ename = name_map.get(row['氏名'], "Staff")
        pdf.cell(20, 10, ename, 1)
        pdf.cell(25, 10, f"{int(row['実績SKU'])} / {int(row['目標SKU合計'])}", 1)
        pdf.cell(15, 10, f"{int(row['SKU差分']):+}", 1)
        pdf.cell(20, 10, str(row['達成率']), 1)
        pdf.cell(30, 10, f"{int(row['売上']):,}", 1)
        pdf.cell(30, 10, f"{int(row['人件費']):,}", 1)
        
        r_prof = int(row['利益'])
        psign = "+" if r_prof >= 0 else "-"
        pdf.cell(30, 10, f"{psign}{abs(r_prof):,}", 1); pdf.ln()
    
    # 確実にbytesで返す
    return pdf.output(dest='S').encode('latin-1')

# --- データのクリーンアップ関数 ---
def clean_all_data():
    for col in ['シフト日数', '調整時間', '交通費']:
        st.session_state.shift_df[col] = pd.to_numeric(st.session_state.shift_df[col], errors='coerce').fillna(0)
    st.session_state.shift_df['合計時間'] = (st.session_state.shift_df['シフト日数'] * 8.0) + st.session_state.shift_df['調整時間']
    if not st.session_state.sku_db.empty:
        for col in ['実績SKU', '総カット数']:
            st.session_state.sku_db[col] = pd.to_numeric(st.session_state.sku_db[col], errors='coerce').fillna(0).astype(int)

clean_all_data()

# --- 2. 画面構成 ---
st.title("📸 rubyohoto 撮影収支管理")
tab1, tab2, tab3 = st.tabs(["📉 収支・時間集計", "📝 実績入力・コスト設定", "⚙️ 各種設定"])

# --- タブ1：収支・時間集計 ---
with tab1:
    st.header("📊 総合レポート")

    s_merge = st.session_state.shift_df.rename(columns={'名前': '氏名'})
    shift_summary = s_merge.groupby('氏名').agg({'シフト日数': 'sum', '合計時間': 'sum', '調整時間': 'sum', '交通費': 'sum'}).reset_index()

    if not st.session_state.sku_db.empty:
        calc_df = pd.merge(st.session_state.sku_db, st.session_state.b_df, left_on="ブランド", right_on="ブランド名", how="left")
        calc_df['売上金額'] = calc_df['総カット数'] * calc_df['カット単価'].fillna(0)
        sku_summary = calc_df.groupby('氏名').agg({'実績SKU': 'sum', '総カット数': 'sum', '売上金額': 'sum'}).reset_index()
    else:
        sku_summary = pd.DataFrame(columns=['氏名', '実績SKU', '総カット数', '売上金額'])

    final = pd.merge(st.session_state.m_df, sku_summary, on='氏名', how='left').fillna(0)
    final = pd.merge(final, shift_summary, on='氏名', how='left').fillna(0)
    
    final['人件費'] = (final['日給'] * final['シフト日数']) + final['交通費']
    final['利益'] = final['売上金額'] - final['人件費']
    final['目標SKU合計'] = final['目標SKU'] * final['シフト日数']
    final['SKU差分'] = final['実績SKU'] - final['目標SKU合計']
    
    def calc_achievement(row):
        if row['目標SKU合計'] > 0:
            return f"{(row['実績SKU'] / row['目標SKU合計']) * 100:.1f}%"
        return "0.0%"
    final['達成率'] = final.apply(calc_achievement, axis=1)

    final['氏名'] = pd.Categorical(final['氏名'], categories=name_order, ordered=True)
    final = final.sort_values('氏名')

    total_adj = shift_summary['調整時間'].sum()
    total_shifts = shift_summary['シフト日数'].sum()
    t_prof = int(final['利益'].sum())
    t_prof_str = f"+¥{t_prof:,}" if t_prof > 0 else f"-¥{abs(t_prof):,}" if t_prof < 0 else "¥0"

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("総売上", f"¥{int(final['売上金額'].sum()):,}")
    m2.metric("総人件費", f"¥{int(final['人件費'].sum()):,}")
    m3.metric("合計利益", t_prof_str)
    m4.metric("合計シフト", f"{total_shifts}日")
    m5.metric("合計調整時間", f"{total_adj:+.1f}h", delta=total_adj)

    st.divider()
    st.subheader("💰 利益分布")
    chart_df = final[['氏名', '利益']].copy()
    chart_df['グラフ色'] = chart_df['利益'].apply(lambda x: '#FF4B4B' if x < 0 else '#0068C9')
    st.bar_chart(chart_df, x='氏名', y='利益', color='グラフ色')

    st.subheader("📋 詳細レポートテーブル")
    disp_df = final[['氏名', '実績SKU', '目標SKU合計', 'SKU差分', '達成率', 'シフト日数', '調整時間', '売上金額', '人件費', '利益']].rename(columns={'売上金額':'売上'})
    
    st.dataframe(disp_df.style.format({
        "売上": "¥{:,.0f}",
        "人件費": "¥{:,.0f}",
        "利益": lambda x: f"+¥{int(x):,}" if x > 0 else (f"-¥{abs(int(x)):,}" if x < 0 else "¥0"), 
        "調整時間": "{:+.1f}h", 
        "実績SKU": "{:.0f} SKU",
        "目標SKU合計": "{:.0f} SKU",
        "SKU差分": "{:+.0f} SKU"
    }), use_container_width=True, hide_index=True)

    # ★ 100%バグらないPDFダウンロードボタン
    try:
        pdf_data = create_pdf(disp_df, final['売上金額'].sum(), final['人件費'].sum(), final['利益'].sum(), total_adj)
        st.download_button(
            label="📄 レポートをPDFで保存",
            data=pdf_data,
            file_name=f"report_{datetime.date.today()}.pdf",
            mime="application/pdf",
            key="pdf_download_btn"
        )
    except Exception as e:
        st.error(f"PDF生成エラー回避中: {e}")

# --- タブ2：実績入力 ---
with tab2:
    st.subheader("⏱️ カメラマン別状況")
    cols = st.columns(len(name_order))
    shift_calc = st.session_state.shift_df.groupby('名前').agg({'シフト日数': 'sum', '調整時間': 'sum', '合計時間': 'sum'}).reset_index()
    for i, name in enumerate(name_order):
        p_data = shift_calc[shift_calc['名前'] == name]
        p_total = p_data['合計時間'].iloc[0] if not p_data.empty else 0.0
        p_adj = p_data['調整時間'].iloc[0] if not p_data.empty else 0.0
        cols[i].metric(label=f"👤 {name}", value=f"{p_total:.1f}h", delta=f"{p_adj:+.1f}h")

    st.divider()
    st.subheader("❶ シフト・コスト設定")
    edited_shift = st.data_editor(
        st.session_state.shift_df, 
        column_order=["名前", "期間", "シフト日数", "合計時間", "調整時間", "交通費"],
        disabled=["合計時間"], hide_index=True, key="sh_editor_v19", use_container_width=True
    )
    if not edited_shift.equals(st.session_state.shift_df):
        st.session_state.shift_df = edited_shift
        clean_all_data()
        st.rerun()
    
    st.divider()
    st.subheader("❷ 撮影実績入力")
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
        i_date = c1.date_input("撮影日")
        i_name = c2.selectbox("カメラマン", name_order)
        in_brand = c3.selectbox("ブランド", st.session_state.b_df["ブランド名"].tolist())
        i_sku = c4.number_input("実績SKU", min_value=0, step=1)
        i_cut = c5.number_input("総カット数", min_value=0, step=1)
        
        if st.button("実績を追加保存", use_container_width=True):
            new = pd.DataFrame([{"日付": str(i_date), "氏名": i_name, "ブランド": in_brand, "実績SKU": int(i_sku), "総カット数": int(i_cut)}])
            st.session_state.sku_db = pd.concat([st.session_state.sku_db, new], ignore_index=True)
            clean_all_data()
            st.rerun()

    st.write("▼ 実績リスト")
    st.session_state.sku_db = st.data_editor(
        st.session_state.sku_db, num_rows="dynamic", use_container_width=True, key="sku_editor_v19",
        column_config={
            "氏名": st.column_config.SelectboxColumn("氏名", options=name_order, required=True),
            "ブランド": st.column_config.SelectboxColumn("ブランド", options=st.session_state.b_df["ブランド名"].tolist(), required=True),
            "実績SKU": st.column_config.NumberColumn("実績SKU", step=1),
            "総カット数": st.column_config.NumberColumn("総カット数", step=1)
        }
    )

# --- タブ3：設定 ---
with tab3:
    ca, cb = st.columns(2)
    ca.subheader("👥 氏名・日給設定")
    st.session_state.m_df = st.data_editor(st.session_state.m_df, hide_index=True, key="m_v19")
    cb.subheader("🏷️ ブランド・単価設定")
    st.session_state.b_df = st.data_editor(st.session_state.b_df, hide_index=True, key="b_v19")

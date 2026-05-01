import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="rubyohoto 撮影収支", layout="wide")

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
        {"名前": "森さん", "期間": "2026/05 第1期", "シフト日数": 6, "合計時間": 0.0, "調整時間": -2.0, "交通費": 816},
        {"名前": "宇田さん", "期間": "2026/05 第1期", "シフト日数": 4, "合計時間": 0.0, "調整時間": 0.0, "交通費": 0},
        {"名前": "三沖さん", "期間": "2026/05 第1期", "シフト日数": 3, "合計時間": 0.0, "調整時間": 0.0, "交通費": 0},
        {"名前": "野澤さん", "期間": "2026/05 第1期", "シフト日数": 1, "合計時間": 0.0, "調整時間": 0.0, "交通費": 0}
    ])

if 'sku_db' not in st.session_state:
    st.session_state.sku_db = pd.DataFrame(columns=["日付", "氏名", "ブランド", "実績SKU", "総カット数"])

# --- ★ データ保護処理 (Noneをゼロに変換) ---
def sanitize_shift_data():
    for col in ['シフト日数', '調整時間', '交通費']:
        st.session_state.shift_df[col] = pd.to_numeric(st.session_state.shift_df[col], errors='coerce').fillna(0)
    # 合計時間を再計算 (1シフト=8時間)
    st.session_state.shift_df['合計時間'] = (st.session_state.shift_df['シフト日数'] * 8.0) + st.session_state.shift_df['調整時間']

# 初回・再読み込み時に必ずクリーンアップ
sanitize_shift_data()

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
    final['原価合計'] = (final['日給'] * final['シフト日数']) + final['交通費']
    final['利益'] = final['売上金額'] - final['原価合計']

    total_adj = shift_summary['調整時間'].sum()
    total_shifts = shift_summary['シフト日数'].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("総売上", f"¥{int(final['売上金額'].sum()):,}")
    m2.metric("合計利益", f"¥{int(final['利益'].sum()):,}")
    m3.metric("チーム全体シフト", f"{total_shifts}日")
    m4.metric("チーム全体調整時間", f"{total_adj:+.1f}h", delta=total_adj, delta_color="normal")

    st.divider()
    c_l, c_r = st.columns(2)
    with c_l:
        st.write("💰 利益分布")
        st.bar_chart(final.set_index('氏名')['利益'])
    with c_r:
        st.write("⏳ 調整時間状況 (+/-)")
        st.bar_chart(final.set_index('氏名')['調整時間'])

    st.subheader("📋 詳細レポートテーブル")
    disp_df = final[['氏名', '実績SKU', '総カット数', 'シフト日数', '合計時間', '調整時間', '売上金額', '利益']].rename(columns={'売上金額':'売上'})
    st.dataframe(disp_df.style.format({"売上": "¥{:,.0f}", "利益": "¥{:,.0f}", "調整時間": "{:+.1f}h", "合計時間": "{:.1f}h"}), use_container_width=True, hide_index=True)


# --- タブ2：コスト設定と実績入力 ---
with tab2:
    st.subheader("⏱️ カメラマン別：シフト＆調整時間 (+/-)")
    names = st.session_state.m_df['氏名'].tolist()
    cols = st.columns(len(names))
    
    shift_calc = st.session_state.shift_df.groupby('名前').agg({'シフト日数': 'sum', '調整時間': 'sum', '合計時間': 'sum'}).reset_index()
    
    for i, name in enumerate(names):
        person_data = shift_calc[shift_calc['名前'] == name]
        p_shift = person_data['シフト日数'].iloc[0] if not person_data.empty else 0
        p_adj = person_data['調整時間'].iloc[0] if not person_data.empty else 0.0
        p_total = person_data['合計時間'].iloc[0] if not person_data.empty else 0.0
        cols[i].metric(label=f"👤 {name}", value=f"{p_total:.1f}h", delta=f"{p_adj:+.1f}h (調整)", delta_color="normal")

    st.divider()

    st.subheader("❶ シフト・コスト設定")
    # 入力を受け付けた後、すぐにNoneを取り除く処理を走らせるための関数
    def on_shift_change():
        sanitize_shift_data()

    st.session_state.shift_df = st.data_editor(
        st.session_state.shift_df, 
        column_order=["名前", "期間", "シフト日数", "合計時間", "調整時間", "交通費"],
        disabled=["合計時間"], 
        hide_index=True, 
        key="sh_tab2_auto",
        on_change=on_shift_change,
        use_container_width=True
    )
    
    st.divider()
    st.subheader("❷ 撮影実績入力")
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
        i_date = c1.date_input("撮影日")
        i_name = c2.selectbox("カメラマン", names)
        in_brand = c3.selectbox("ブランド", st.session_state.b_df["ブランド名"].tolist())
        i_sku = c4.number_input("SKU数", min_value=0)
        i_cut = c5.number_input("総カット数", min_value=0)
        if st.button("実績を追加保存", use_container_width=True):
            new = pd.DataFrame([{"日付": str(i_date), "氏名": i_name, "ブランド": in_brand, "実績SKU": i_sku, "総カット数": i_cut}])
            st.session_state.sku_db = pd.concat([st.session_state.sku_db, new], ignore_index=True)
            st.rerun()

    st.write("▼ 実績リスト")
    st.session_state.sku_db = st.data_editor(st.session_state.sku_db, num_rows="dynamic", use_container_width=True, key="sku_tab2_auto")


# --- タブ3：設定 ---
with tab3:
    ca, cb = st.columns(2)
    ca.subheader("👥 氏名・日給設定")
    st.session_state.m_df = st.data_editor(st.session_state.m_df, hide_index=True, key="m_tab3_auto")
    cb.subheader("🏷️ ブランド・単価設定")
    st.session_state.b_df = st.data_editor(st.session_state.b_df, hide_index=True, key="b_tab3_auto")

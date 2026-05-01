import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

st.set_page_config(page_title="撮影収支管理システム", layout="wide")

# --- ファイル保存設定 ---
MASTER_FILE = "camera_master.csv"
BRAND_FILE = "brand_master.csv"
PLAN_FILE = "shift_plan.csv"
SKU_FILE = "daily_sku_records.csv"

def load_csv(file_name, columns=None, default_rows=None):
    if os.path.exists(file_name):
        df = pd.read_csv(file_name)
        if columns:
            for col in columns:
                if col not in df.columns:
                    df[col] = 0 if ("数" in col or "単価" in col or "売上" in col) else "未設定"
        return df
    df = pd.DataFrame(default_rows) if default_rows else pd.DataFrame(columns=columns)
    df.to_csv(file_name, index=False)
    return df

def save_csv(df, file_name):
    df.to_csv(file_name, index=False)

# --- データ初期化 ---
if 'master_data' not in st.session_state:
    st.session_state['master_data'] = load_csv(MASTER_FILE, columns=["氏名", "日給", "目標SKU"])

if 'brand_data' not in st.session_state:
    st.session_state['brand_data'] = load_csv(BRAND_FILE, default_rows=[
        {"ブランド名": "ブランドA", "SKU単価": 1900},
        {"ブランド名": "ブランドB", "SKU単価": 2500}
    ])

if 'shift_plan_db' not in st.session_state:
    st.session_state['shift_plan_db'] = load_csv(PLAN_FILE, columns=["氏名", "期間", "シフト日数", "調整時間", "交通費"])

if 'daily_sku' not in st.session_state:
    # 「総カット数」を内部的にも読み飛ばす設定
    st.session_state['daily_sku'] = load_csv(SKU_FILE, columns=["日付", "氏名", "ブランド", "実績SKU"])

# 固定の並び順
current_member_list = ["森さん", "宇田さん", "三沖さん", "野澤さん"]
master_dict = st.session_state['master_data'].set_index("氏名").to_dict("index")
brand_dict = st.session_state['brand_data'].set_index("ブランド名")["SKU単価"].to_dict()

# サイドバー
st.sidebar.header("📅 期間選択")
month_focus = st.sidebar.selectbox("対象月", ["2026/05", "2026/06", "2026/07"])
period_focus = st.sidebar.radio("期間区分", ["第1期 (1-20日)", "第2期 (21-末日)"])
full_p_label = f"{month_focus} {period_focus}"

tab1, tab2, tab3 = st.tabs(["📉 収支分析", "📝 実績入力・シフト設定", "⚙️ 各種設定"])

# --- 共通計算 ---
plan_db = st.session_state['shift_plan_db'].copy()
sku_db = st.session_state['daily_sku'].copy()

if not sku_db.empty:
    sku_db['日付'] = pd.to_datetime(sku_db['日付'], errors='coerce')
    sku_db = sku_db.dropna(subset=['日付'])
    def get_p(d): return f"{d.year}/{d.month:02d} {'第1期 (1-20日)' if d.day <= 20 else '第2期 (21-末日)'}"
    sku_db['期間判定'] = sku_db['日付'].apply(get_p)
    target_skus = sku_db[sku_db['期間判定'] == full_p_label].copy()
    target_skus['売上'] = target_skus.apply(lambda x: x['実績SKU'] * brand_dict.get(x['ブランド'], 0), axis=1)
else:
    target_skus = pd.DataFrame(columns=["氏名", "実績SKU", "売上"])

sum_p = plan_db[plan_db['期間'] == full_p_label].groupby('氏名', as_index=False).agg({'シフト日数':'sum', '調整時間':'sum', '交通費':'sum'})
sum_s = target_skus.groupby('氏名', as_index=False).agg({'実績SKU':'sum', '売上':'sum'})
final = pd.merge(sum_p, sum_s, on='氏名', how='left').fillna(0)
final['氏名'] = pd.Categorical(final['氏名'], categories=current_member_list, ordered=True)
final = final.sort_values('氏名')

# ------------------------------------------
# タブ1：分析
# ------------------------------------------
with tab1:
    if not final.empty:
        def calc_biz(row):
            m = master_dict.get(row['氏名'], {"日給":0})
            t_h = (row['シフト日数'] * 8) + row['調整時間']
            cost = ((float(m['日給'])/8.0) * float(t_h)) + float(row['交通費'])
            return pd.Series([cost, row['売上'] - cost])
        
        final[['総原価', '粗利益']] = final.apply(calc_biz, axis=1)

        st.header(f"📊 {full_p_label} 収支レポート")
        m1, m2, m3 = st.columns(3)
        m1.metric("総売上高", f"¥{int(final['売上'].sum()):,}")
        m2.metric("総原価", f"¥{int(final['総原価'].sum()):,}")
        m3.metric("粗利益", f"¥{int(final['粗利益'].sum()):,}")

        st.divider()
        fig = px.bar(final, x='氏名', y='粗利益', color='粗利益', color_continuous_scale="RdYlGn", title="カメラマン別：粗利益貢献")
        fig.update_traces(texttemplate='¥%{y:,.0f}', textposition='outside')
        fig.update_layout(yaxis_tickformat=',', xaxis={'categoryorder':'array', 'categoryarray':current_member_list})
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 詳細データ")
        st.dataframe(final[["氏名", "シフト日数", "実績SKU", "売上", "総原価", "粗利益"]].style.format({
            "実績SKU": "{:,.0f}", "売上": "¥{:,.0f}", "総原価": "¥{:,.0f}", "粗利益": "¥{:,.0f}"
        }).map(lambda v: 'color:red;font-weight:bold;' if v<0 else 'color:blue;font-weight:bold;' if v>0 else '', subset=['粗利益']), use_container_width=True, hide_index=True)
    else:
        st.info("集計対象のデータがありません。")

# ------------------------------------------
# タブ2：実績入力
# ------------------------------------------
with tab2:
    st.subheader("❶ シフト・コスト設定")
    all_p = st.session_state['shift_plan_db']
    cur_p = all_p[all_p['期間'] == full_p_label].copy()
    if cur_p.empty:
        cur_p = pd.DataFrame({"氏名": current_member_list, "期間": full_p_label, "シフト日数": 0, "調整時間": 0.0, "交通費": 0})
    cur_p['氏名'] = pd.Categorical(cur_p['氏名'], categories=current_member_list, ordered=True)
    cur_p = cur_p.sort_values('氏名')
    edited_p = st.data_editor(cur_p, use_container_width=True, hide_index=True, key=f"p_ed_{full_p_label}")
    if not edited_p.drop(columns="期間").equals(cur_p.drop(columns="期間")):
        st.session_state['shift_plan_db'] = pd.concat([all_p[all_p['期間'] != full_p_label], edited_p], ignore_index=True)
        save_csv(st.session_state['shift_plan_db'], PLAN_FILE)
        st.rerun()

    st.divider()
    st.subheader("❷ 実績入力")
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
    d_date = c1.date_input("撮影日", datetime.date.today())
    d_name = c2.selectbox("カメラマン", current_member_list)
    d_brand = c3.selectbox("ブランド", list(brand_dict.keys()))
    d_sku = c4.number_input("SKU数", min_value=0, step=1)
    
    if c5.button("追加", use_container_width=True):
        new_row = pd.DataFrame([{"日付": str(d_date), "氏名": d_name, "ブランド": d_brand, "実績SKU": d_sku}])
        st.session_state['daily_sku'] = pd.concat([st.session_state['daily_sku'], new_row], ignore_index=True)
        save_csv(st.session_state['daily_sku'], SKU_FILE)
        st.rerun()
    
    if not st.session_state['daily_sku'].empty:
        st.write("▼ 実績リスト（修正・削除可能）")
        sku_edit = st.data_editor(st.session_state['daily_sku'], num_rows="dynamic", use_container_width=True, hide_index=True)
        if not sku_edit.equals(st.session_state['daily_sku']):
            st.session_state['daily_sku'] = sku_edit
            save_csv(sku_edit, SKU_FILE)
            st.rerun()

with tab3:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.subheader("👥 カメラマン設定")
        edited_m = st.data_editor(st.session_state['master_data'], num_rows="dynamic", hide_index=True)
        if not edited_m.equals(st.session_state['master_data']):
            st.session_state['master_data'] = edited_m
            save_csv(edited_m, MASTER_FILE)
            st.rerun()
    with col_s2:
        st.subheader("🏷️ ブランド・単価設定")
        edited_b = st.data_editor(st.session_state['brand_data'], num_rows="dynamic", hide_index=True)
        if not edited_b.equals(st.session_state['brand_data']):
            st.session_state['brand_data'] = edited_b
            save_csv(edited_b, BRAND_FILE)
            st.rerun()

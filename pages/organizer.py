import streamlit as st
import zipfile
import io
import os
import csv
import re

st.set_page_config(page_title="VW撮影データ仕分けツール", layout="centered")

# --- 初期化 ---
if 'zip_data' not in st.session_state:
    st.session_state.zip_data = None
    st.session_state.moved_count = 0
    st.session_state.unmatched_files = []
    st.session_state.logs = []

if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

def normalize(text):
    """ファイル名やIDから記号を抜いて大文字にし、比較しやすくする関数"""
    if not text: return ""
    return re.sub(r'[^A-Z0-9]', '', str(text).upper())

st.title("📦 VW撮影データ仕分けツール (完全版)")
st.write("CSVの指示書を読み込み、トルソーとモデルの画像を**同じ品番フォルダ**に自動で仕分けしてZIP化します。")
st.divider()

# --- 1. アップロードエリア ---
st.subheader("1. 撮影指示管理シート (CSV) を選択")
csv_file = st.file_uploader("CSVファイルをアップロードしてください", type=['csv'])

st.subheader("2. 画像ファイルを選択")
image_files = st.file_uploader(
    "仕分けたい画像（トルソー・モデル両方）を選択", 
    type=['jpg', 'jpeg', 'png'], 
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

# --- 2. 仕分け実行ロジック ---
if csv_file and image_files:
    if st.button("🚀 仕分け実行（トルソー・モデルを同じフォルダへ）", type="primary", use_container_width=True):
        
        # --- CSVの読み込みと解読 ---
        csv_text = None
        for enc in ['utf-8-sig', 'shift_jis', 'cp932']:
            try:
                csv_text = csv_file.getvalue().decode(enc)
                break
            except UnicodeDecodeError:
                continue
                
        if not csv_text:
            st.error("エラー: CSVファイルの文字コードが読み取れませんでした。")
            st.stop()

        csv_data = list(csv.reader(io.StringIO(csv_text)))
        move_rules = {}
        start_reading = False
        
        for row in csv_data:
            if not row: continue
            if "入荷日" in row[0] or (len(row) > 1 and "撮影日" in row[1]):
                start_reading = True
                continue
            if not start_reading: continue
            if len(row) < 19: continue
            
            torso_id = row[17].strip()
            model_id = row[18].strip()

            if not torso_id: continue
            
            # フォルダ名はトルソーID（末尾のアンダーバー除去）を基準にする
            folder_name = torso_id.rstrip('_')
            
            # トルソーIDもモデルIDも、同じフォルダ名に紐付ける
            move_rules[normalize(torso_id)] = folder_name
            if model_id:
                move_rules[normalize(model_id)] = folder_name

        if not move_rules:
            st.warning("警告: 有効な品番データが見つかりませんでした。CSVの中身を確認してください。")
            st.stop()

        # --- 画像の仕分けとZIP作成 ---
        zip_buffer = io.BytesIO()
        sorted_keys = sorted(move_rules.keys(), key=len, reverse=True)
        moved_count = 0
        unmatched = []
        logs = []

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file in image_files:
                filename = file.name
                norm_filename = normalize(filename)
                matched = False
                
                # 正規化（記号抜き）したファイル名の中に、CSVのIDが含まれているかチェック
                for search_key in sorted_keys:
                    if search_key in norm_filename:
                        target_folder_name = move_rules[search_key]
                        
                        # ZIPの中に保存（フォルダ名 / ファイル名）
                        zip_path = f"仕分け結果/{target_folder_name}/{filename}"
                        zip_file.writestr(zip_path, file.read())
                        
                        moved_count += 1
                        logs.append(f"✓ {filename} ➔ [{target_folder_name}]")
                        matched = True
                        break 
                
                if not matched:
                    unmatched.append(filename)

        st.session_state.zip_data = zip_buffer.getvalue()
        st.session_state.moved_count = moved_count
        st.session_state.unmatched_files = unmatched
        st.session_state.logs = logs
        
        st.success("✅ 仕分けが完了しました！下のボタンからダウンロードしてください。")

# --- 3. 結果とダウンロード ---
if st.session_state.zip_data:
    st.divider()
    
    st.metric("📁 正常に仕分けできた画像数", f"{st.session_state.moved_count} 枚")
    
    st.download_button(
        label="📥 仕分け済みZIPをダウンロード",
        data=st.session_state.zip_data,
        file_name="VW_organized_photos.zip",
        mime="application/zip",
        use_container_width=True
    )
    
    if st.session_state.unmatched_files:
        st.warning(f"⚠️ 以下の {len(st.session_state.unmatched_files)} 枚は、CSVのリストと一致せず仕分けられませんでした。")
        with st.expander("仕分けられなかったファイル一覧"):
            for uf in st.session_state.unmatched_files:
                st.write(uf)

    with st.expander("📝 処理ログを確認する"):
        for log in st.session_state.logs:
            st.text(log)
            
    if st.button("🔄 リセットしてやり直す"):
        st.session_state.zip_data = None
        st.session_state.uploader_key += 1
        st.rerun()

import streamlit as st
import zipfile
import io
import os
import csv
import re

st.set_page_config(page_title="VW撮影データ仕分けツール", layout="centered")

# --- セッション状態の初期化 ---
if 'zip_data' not in st.session_state:
    st.session_state.zip_data = None
    st.session_state.moved_count = 0
    st.session_state.logs = []

if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

st.title("📦 VW撮影データ仕分けツール (Web版)")
st.warning("⚠️ 数GBになる重いTIFFデータ（Dropbox内のデータ）の仕分けは、ブラウザが重くなるためMac上の専用ツールで行ってください。こちらはJPG等の軽量データ用です。")
st.divider()

st.subheader("画像ファイルを選択 (自動判定)")
image_files = st.file_uploader(
    "軽量な画像（JPG/PNG等）を選択", 
    type=['jpg', 'jpeg', 'png'], 
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

# --- 仕分け実行ロジック ---
if image_files:
    if st.button("🚀 仕分け実行（ZIP作成）", type="primary", use_container_width=True):
        zip_buffer = io.BytesIO()
        moved_count = 0
        logs = []

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file in image_files:
                filename = file.name
                name_part = os.path.splitext(filename)[0]
                
                # ハイフンをアンダーバーに統一 ＆ モデル文字(_M_)を除去して同じ品番にまとめる
                clean_name = name_part.replace("-", "_")
                clean_name = re.sub(r'_[mM]_', '_', clean_name)
                
                # 末尾の連番をカットして品番フォルダ名に
                parts = clean_name.split('_')
                if len(parts) > 1:
                    folder_name = "_".join(parts[:-1])
                else:
                    folder_name = clean_name
                
                # ZIP内に保存（完成したフォルダ名の中に入れる）
                zip_path = f"仕分け結果/{folder_name}/{filename}"
                zip_file.writestr(zip_path, file.read())
                moved_count += 1
                logs.append(f"✓ {filename} ➔ [{folder_name}]")

        # 処理終了後のデータ保存
        st.session_state.zip_data = zip_buffer.getvalue()
        st.session_state.moved_count = moved_count
        st.session_state.logs = logs
        
        st.success("✅ 仕分けが完了しました！下のボタンからダウンロードしてください。")

# --- 結果とダウンロード ---
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

    with st.expander("📝 処理ログを確認する"):
        for log in st.session_state.logs:
            st.text(log)
            
    if st.button("🔄 リセットしてやり直す"):
        st.session_state.zip_data = None
        st.session_state.uploader_key += 1
        st.rerun()

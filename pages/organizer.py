import streamlit as st
import zipfile
import io
import os

st.set_page_config(page_title="PhotoOrganizer", layout="centered")

st.title("📦 PhotoOrganizer - ブツ撮り仕分け版")
st.write("画像をアップロードすると、ファイル名のアンダーバー(`_`)基準で自動的にフォルダ分けされたZIPファイルを作成します。")

# --- セッション状態の初期化 ---
if 'zip_data' not in st.session_state:
    st.session_state.zip_data = None
    st.session_state.processed_count = 0
    st.session_state.folder_count = 0
    st.session_state.logs = []

# --- 1. アップロードエリア ---
uploaded_files = st.file_uploader(
    "仕分けたい画像を選択（ドラッグ＆ドロップで複数選択可）", 
    type=['jpg', 'jpeg', 'png'], 
    accept_multiple_files=True
)

# --- 2. 仕分け処理 ---
if uploaded_files:
    if st.button("⚙️ 仕分け開始", type="primary", use_container_width=True):
        # メモリ上にZIPファイルを作成するための準備
        zip_buffer = io.BytesIO()
        folders_created = set()
        processed_count = 0
        logs = []
        
        # ZIPファイルへの書き込み開始
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file in uploaded_files:
                filename = file.name
                name_part = os.path.splitext(filename)[0]
                parts = name_part.split('_')
                
                # アンダーバーで区切って、末尾以外をフォルダ名にする
                if len(parts) > 1:
                    folder_name = "_".join(parts[:-1])
                else:
                    folder_name = name_part
                
                folders_created.add(folder_name)
                processed_count += 1
                
                # ZIP内の仮想的な保存パスを作成（スラッシュ区切り）
                zip_path = f"{folder_name}/{filename}"
                
                # ZIPにファイルを書き込む
                zip_file.writestr(zip_path, file.read())
                logs.append(f"✓ {filename} ➔ [{folder_name}] フォルダへ")
                
        # 処理が終わったらデータをセッションに保存
        st.session_state.zip_data = zip_buffer.getvalue()
        st.session_state.processed_count = processed_count
        st.session_state.folder_count = len(folders_created)
        st.session_state.logs = logs
        
        st.success("✅ 仕分けが完了しました！下のボタンからダウンロードしてください。")

# --- 3. 結果表示とダウンロード ---
if st.session_state.zip_data:
    st.divider()
    
    # メトリクス表示
    col1, col2 = st.columns(2)
    col1.metric("📸 処理した合計枚数", f"{st.session_state.processed_count} 枚")
    col2.metric("📁 作成したフォルダ数", f"{st.session_state.folder_count} フォルダ")
    
    # ダウンロードボタン
    st.download_button(
        label="📥 仕分け済みZIPをダウンロード",
        data=st.session_state.zip_data,
        file_name="organized_photos.zip",
        mime="application/zip",
        use_container_width=True
    )
    
    # 処理ログの表示
    with st.expander("📝 処理ログを確認する"):
        for log in st.session_state.logs:
            st.text(log)
    
    # リセットボタン
    if st.button("🔄 リセットしてやり直す"):
        st.session_state.zip_data = None
        st.rerun()

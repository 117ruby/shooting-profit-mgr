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
    if not text: return ""
    return re.sub(r'[^A-Z0-9]', '', str(text).upper())

st.title("📦 VW撮影データ仕分けツール")
st.write("画像をアップロードするだけで、トルソーとモデル(`_M_`)を**同じ品番フォルダ**に自動でまとめます。")
st.divider()

# --- 1. アップロードエリア ---
st.subheader("1. 撮影指示管理シート (CSV) 💡無くてもOK！")
csv_file = st.file_uploader("あればアップロード（※無い場合はファイル名から自動で同じ品番にまとめます）", type=['csv'])

st.subheader("2. 画像ファイルを選択 (必須)")
image_files = st.file_uploader(
    "仕分けたい画像（トルソー・モデル両方）を選択", 
    type=['jpg', 'jpeg', 'png'], 
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

# --- 2. 仕分け実行ロジック ---
if image_files:
    if st.button("🚀 仕分け実行（トルソー・モデルを同じフォルダへ）", type="primary", use_container_width=True):
        
        zip_buffer = io.BytesIO()
        moved_count = 0
        unmatched = []
        logs = []

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            
            # ==========================================
            # パターンA：CSVがある場合（指示書ベースで厳密に）
            # ==========================================
            if csv_file:
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
                    folder_name = torso_id.rstrip('_').replace("-", "_") # フォルダ名も_に統一
                    move_rules[normalize(torso_id)] = folder_name
                    if model_id:
                        move_rules[normalize(model_id)] = folder_name

                sorted_keys = sorted(move_rules.keys(), key=len, reverse=True)
                
                for file in image_files:
                    filename = file.name
                    norm_filename = normalize(filename)
                    matched = False
                    
                    for search_key in sorted_keys:
                        if search_key in norm_filename:
                            target_folder_name = move_rules[search_key]
                            zip_path = f"仕分け結果/{target_folder_name}/{filename}"
                            zip_file.writestr(zip_path, file.read())
                            moved_count += 1
                            logs.append(f"✓ {filename} ➔ [{target_folder_name}]")
                            matched = True
                            break 
                    
                    if not matched:
                        unmatched.append(filename)

            # ==========================================
            # パターンB：CSVが無い場合（ファイル名から全自動判定）
            # ==========================================
            else:
                for file in image_files:
                    filename = file.name
                    name_part = os.path.splitext(filename)[0]
                    
                    # 1. 邪魔なハイフン(-)をアンダーバー(_)に変換して統一する
                    clean_name = name_part.replace("-", "_")
                    
                    # 2. モデルの目印(_m_ や _M_)をただのアンダーバー(_)にしてトルソーの形に寄せる
                    clean_name = clean_name.replace("_m_", "_").replace("_M_", "_")
                    
                    # 3. 末尾の連番(_1, _2など)をカットして品番フォルダ名にする
                    parts = clean_name.split('_')
                    if len(parts) > 1:
                        folder_name = "_".join(parts[:-1])
                    else:
                        folder_name = clean_name
                    
                    # ZIP内に保存（完成したフォルダ名の中に入れる）
                    zip_path = f"仕分け結果/{folder_name}/{filename}"
                    zip_file.writestr(zip_path, file.read())
                    moved_count += 1
                    logs.append(f"✓ {filename} ➔ [{folder_name}] (自動判定)")

        # 処理終了後のデータ保存
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
        st.warning(f"⚠️ 以下の {len(st.session_state.unmatched_files)} 枚は、CSVと一致せず仕分けられませんでした。")
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

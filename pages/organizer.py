import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import re
from pathlib import Path

def normalize(text):
    if not text: return ""
    return re.sub(r'[^A-Z0-9]', '', str(text).upper())

def smart_organize_dropbox():
    target_dir = filedialog.askdirectory(title="【Dropbox用】画像フォルダを選択してください")
    if not target_dir:
        return
    
    target_path = Path(target_dir)
    files = [f for f in target_path.iterdir() if f.is_file() and f.suffix.lower() in ['.tiff', '.tif', '.jpg', '.jpeg', '.png']]
    
    if not files:
        messagebox.showinfo("情報", "対象の画像ファイルが見つかりませんでした。")
        return

    moved_count = 0
    
    for file_path in files:
        filename = file_path.name
        name_part = file_path.stem
        
        # ハイフンをアンダーバーに統一 ＆ モデル文字除去
        clean_name = name_part.replace("-", "_")
        clean_name = re.sub(r'_[mM]_', '_', clean_name)
        
        # 末尾の連番をカットして品番フォルダ名に
        parts = clean_name.split('_')
        if len(parts) > 1:
            folder_name = "_".join(parts[:-1])
        else:
            folder_name = clean_name
            
        dest_folder = target_path / folder_name
        dest_folder.mkdir(exist_ok=True)
        
        # ★ここがDropbox専用の魔法★
        # Pythonのお節介な移動機能を使わず、Macのシステム(Terminal)に直接「名前だけ変えろ」と命令する
        try:
            # subprocessを使ってMacの 'mv' コマンドを実行（中身をダウンロードしない）
            subprocess.run(["mv", str(file_path), str(dest_folder / filename)], check=True)
            moved_count += 1
        except Exception as e:
            print(f"Error moving {filename}: {e}")

    messagebox.showinfo("完了", f"仕分けが完了しました！\n\n移動したファイル: {moved_count}枚\nクラウドの同期をお待ちください。")

root = tk.Tk()
root.withdraw()
smart_organize_dropbox()

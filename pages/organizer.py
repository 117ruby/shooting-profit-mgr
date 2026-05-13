import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import re
from pathlib import Path

def smart_organize_dropbox():
    target_dir = filedialog.askdirectory(title="【Dropbox用】画像フォルダを選択してください")
    if not target_dir: return
    target_path = Path(target_dir)
    files = [f for f in target_path.iterdir() if f.is_file() and f.suffix.lower() in ['.tiff', '.tif', '.jpg', '.jpeg', '.png']]
    
    if not files:
        messagebox.showinfo("情報", "対象の画像ファイルが見つかりませんでした。")
        return

    moved_count = 0
    for file_path in files:
        filename = file_path.name
        name_part = file_path.stem
        
        clean_name = name_part.replace("-", "_")
        clean_name = re.sub(r'_[mM]_', '_', clean_name)
        parts = clean_name.split('_')
        folder_name = "_".join(parts[:-1]) if len(parts) > 1 else clean_name
            
        dest_folder = target_path / folder_name
        dest_folder.mkdir(exist_ok=True)
        
        try:
            # ダウンロードさせずに名前だけ書き換える魔法
            subprocess.run(["mv", str(file_path), str(dest_folder / filename)], check=True)
            moved_count += 1
        except Exception as e:
            print(f"Error moving {filename}: {e}")

    messagebox.showinfo("完了", f"仕分け完了！\n移動したファイル: {moved_count}枚\nDropboxの同期をお待ちください。")

root = tk.Tk()
root.withdraw()
smart_organize_dropbox()

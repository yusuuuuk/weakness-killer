import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==========================================
# ⚙️ 設定エリア
# ==========================================

# 読み込み用: 列番号（A=0, B=1, C=2, D=3...）
COL_Q_NUM   = 3  # D列: 問題番号（※ここを書き換える場合、番号が消えるので注意！）
COL_IMG_URL = 9  # J列: 画像URL（※作業用列）
COL_SCORE   = 8  # I列: スコア

# 🔥 書き込み設定（重要）
# クリア時に「今日の日付」を書き込む列（1始まり: A=1, B=2, C=3, D=4...）
COL_DATE_WRITE = 4  # 👈 「4」ならD列に書き込みます

# ==========================================

# --- 1. アプリ設定 & 認証 ---
st.set_page_config(page_title="Weakness Killer", page_icon="🔥")
st.title("🔥 Weakness Killer (算数)")

# サイドバー設定
with st.sidebar:
    st.header("🔍 表示フィルタ")
    min_score = st.slider("最低優先度（スコア）", min_value=0, max_value=200, value=80)
    st.caption(f"スコア {min_score} 以上の問題のみ表示中")

# Google Sheetsへの接続
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

try:
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet_url = st.secrets["spreadsheet"]["url"]
    worksheet_name = st.secrets["spreadsheet"]["worksheet_name"]
    sheet = client.open_by_url(sheet_url).worksheet(worksheet_name)
    
except Exception as e:
    st.error(f"認証エラー: {e}")
    st.stop()

# --- 2. 関数定義 ---

def get_data():
    all_values = sheet.get_all_values()
    if len(all_values) < 2:
        return pd.DataFrame()
    headers = all_values[0]
    df = pd.DataFrame(all_values[1:], columns=headers)
    return df

def convert_drive_url(url):
    if not isinstance(url, str): return None
    if "drive.google.com" in url and "id=" in url:
        try:
            file_id = url.split('id=')[1].split('&')[0]
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
        except: return url
    elif "drive.google.com" in url and "/d/" in url:
        try:
            file_id = url.split('/d/')[1].split('/')[0]
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
        except: return url
    return url

# --- 3. メイン処理 ---
df = get_data()

tasks = []

for i, row in df.iterrows():
    try:
        # 必要な列があるかチェック
        if len(row) <= max(COL_Q_NUM, COL_IMG_URL, COL_SCORE): continue

        q_num = row[COL_Q_NUM]
        raw_url = row[COL_IMG_URL]
        
        # 画像URL変換
        img_url = convert_drive_url(raw_url) if str(raw_url).startswith("http") else None

        # スコア取得
        try:
            score = int(float(row[COL_SCORE]))
        except:
            score = 0

        # フィルタリング
        if score >= min_score:
            tasks.append({
                "index": i + 2, # 行番号
                "name": q_num,
                "img": img_url,
                "score": score
            })

    except Exception as e:
        continue

# 並び替え（優先度高い順）
tasks = sorted(tasks, key=lambda x: x["score"], reverse=True)

# --- 4. 画面表示 ---
if not tasks:
    st.info(f"優先度 {min_score} 以上の課題はありません！")
else:
    st.write(f"優先度 **{min_score}** 以上の課題: **{len(tasks)}** 問")
    
    for task in tasks:
        with st.container():
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            
            with c1:
                if task["img"]:
                    st.image(task["img"], use_container_width=True)
                else:
                    st.warning("画像なし")
            
            with c2:
                # 優先度表示
                if task["score"] >= 80:
                    st.error(f"🚨 優先度: {task['score']}")
                else:
                    st.warning(f"⚠️ 優先度: {task['score']}")
                
                st.subheader(task["name"])
                
                # クリアボタン
                if st.button(f"✅ 完了 (日付更新)", key=f"btn_{task['index']}"):
                    # 今日付を取得 (YYYY/MM/DD)
                    today_str = datetime.now().strftime('%Y/%m/%d')
                    
                    # 指定した列(D列なら4)に日付を書き込む
                    sheet.update_cell(task["index"], COL_DATE_WRITE, today_str)
                    
                    st.toast(f"完了！日付を {today_str} に更新しました")
                    import time
                    time.sleep(1)
                    st.rerun()

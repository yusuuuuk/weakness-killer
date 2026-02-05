import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==========================================
# ⚙️ 設定エリア
# ==========================================

# 読み込み設定 (A列=0, B=1, C=2...)
COL_Q_NUM   = 2  # C列: 問題名（※ここを実際のシートに合わせてください！）
COL_IMG_URL = 9  # J列: 画像URL（作業用列）
COL_SCORE   = 8  # I列: スコア

# チェックボックスの列番号 (A=0, B=1...)
COL_LV1     = 5  # F列
COL_LV2     = 6  # G列
COL_LV3     = 7  # H列

# 🔥 書き込み設定 (1始まり: A=1, B=2...)
# 日付を更新する列
COL_DATE_WRITE = 4  # D列 (ここを今日の日付にします)

# ==========================================

# --- 1. アプリ設定 & 認証 ---
st.set_page_config(page_title="Weakness Killer", page_icon="🔥")
st.title("🔥 Weakness Killer (算数)")

with st.sidebar:
    st.header("🔍 表示フィルタ")
    min_score = st.slider("最低優先度", 0, 200, 80)
    st.caption(f"スコア {min_score} 以上の問題を表示")

# Google Sheets接続
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

# --- 2. データ取得 ---
def get_data():
    all_values = sheet.get_all_values()
    if len(all_values) < 2: return pd.DataFrame()
    return pd.DataFrame(all_values[1:], columns=all_values[0])

def convert_drive_url(url):
    if not isinstance(url, str): return None
    if "drive.google.com" in url and "id=" in url:
        try: return f"https://drive.google.com/thumbnail?id={url.split('id=')[1].split('&')[0]}&sz=w1000"
        except: return url
    elif "drive.google.com" in url and "/d/" in url:
        try: return f"https://drive.google.com/thumbnail?id={url.split('/d/')[1].split('/')[0]}&sz=w1000"
        except: return url
    return url

# --- 3. メイン処理 ---
df = get_data()
tasks = []

for i, row in df.iterrows():
    try:
        # 列数チェック
        if len(row) <= max(COL_Q_NUM, COL_IMG_URL, COL_SCORE, COL_LV3): continue

        q_num = row[COL_Q_NUM]
        raw_url = row[COL_IMG_URL]
        img_url = convert_drive_url(raw_url) if str(raw_url).startswith("http") else None

        # スコア取得
        try: score = int(float(row[COL_SCORE]))
        except: score = 0

        # チェックボックス状態取得 ("TRUE"文字判定)
        lv1 = str(row[COL_LV1]).upper() == "TRUE"
        lv2 = str(row[COL_LV2]).upper() == "TRUE"
        lv3 = str(row[COL_LV3]).upper() == "TRUE"

        # 表示条件: Lv3(卒業)以外 かつ スコア条件
        if not lv3 and score >= min_score:
            tasks.append({
                "index": i + 2, # 行番号
                "name": q_num,
                "img": img_url,
                "score": score,
                "lv1": lv1, "lv2": lv2, "lv3": lv3
            })
    except: continue

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
                if task["img"]: st.image(task["img"], use_container_width=True)
                else: st.warning("画像なし")
            
            with c2:
                if task["score"] >= 80: st.error(f"🚨 優先度: {task['score']}")
                else: st.warning(f"⚠️ 優先度: {task['score']}")
                
                st.subheader(task["name"])
                
                # 次にチェックすべき場所を判定
                if task["lv2"]:
                    next_step = "Lv3 (卒業)"
                    check_target_col = COL_LV3 + 1 # 1始まりに変換
                elif task["lv1"]:
                    next_step = "Lv2"
                    check_target_col = COL_LV2 + 1
                else:
                    next_step = "Lv1"
                    check_target_col = COL_LV1 + 1
                
                st.caption(f"Next Step: **{next_step}** クリア")
                
                # ボタン
                btn_label = f"✅ {next_step} 完了！"
                
                if st.button(btn_label, key=f"btn_{task['index']}"):
                    today_str = datetime.now().strftime('%Y/%m/%d')
                    
                    # 1. チェックボックスをONにする
                    sheet.update_cell(task["index"], check_target_col, True)
                    
                    # 2. 日付(D列)を今日に更新する
                    sheet.update_cell(task["index"], COL_DATE_WRITE, today_str)
                    
                    st.toast(f"完了！日付更新＆{next_step}チェック")
                    import time
                    time.sleep(1)
                    st.rerun()

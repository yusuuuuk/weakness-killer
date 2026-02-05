import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# ⚙️ 設定エリア
# ==========================================

# スプレッドシートの「列番号」（A列=0, B列=1...）
# ※ここに「生のURL（https://...）」がある列を指定してください！
COL_Q_NUM   = 3  # D列: 問題番号
COL_IMG_URL = 9  # J列: 画像URL（※先ほど作成した作業用列を指定！）
COL_LV1     = 5  # F列: 1回目
COL_LV2     = 6  # G列: 2回目
COL_LV3     = 7  # H列: 3回目
COL_SCORE   = 8  # I列: スコア

# ==========================================

# --- 1. アプリ設定 & 認証 ---
st.set_page_config(page_title="Weakness Killer", page_icon="🔥")
st.title("🔥 Weakness Killer (算数)")

# サイドバー設定
with st.sidebar:
    st.header("🔍 表示フィルタ")
    # ここで「80」をデフォルト値に設定しています
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

# 行ごとに処理
for i, row in df.iterrows():
    try:
        if len(row) <= max(COL_Q_NUM, COL_IMG_URL, COL_SCORE): continue

        q_num = row[COL_Q_NUM]
        raw_url = row[COL_IMG_URL]
        
        # URL変換
        img_url = convert_drive_url(raw_url) if str(raw_url).startswith("http") else None

        lv1 = str(row[COL_LV1]).upper() == "TRUE"
        lv2 = str(row[COL_LV2]).upper() == "TRUE"
        lv3 = str(row[COL_LV3]).upper() == "TRUE"
        
        # スコア取得
        try:
            score = int(float(row[COL_SCORE]))
        except:
            score = 0

        # 🔥 フィルタリング条件 🔥
        # Lv3未完了 かつ スコアが設定値(80)以上のみ追加
        if not lv3 and score >= min_score:
            tasks.append({
                "index": i + 2,
                "name": q_num,
                "img": img_url,
                "score": score,
                "lv1": lv1, "lv2": lv2, "lv3": lv3
            })

    except Exception as e:
        continue

# 並び替え（優先度高い順）
tasks = sorted(tasks, key=lambda x: x["score"], reverse=True)

# --- 4. 画面表示 ---
if not tasks:
    st.info(f"優先度 {min_score} 以上の課題はありません！")
    if min_score > 0:
        st.caption("サイドバーのスライダーを下げると、他の課題が見えるかもしれません。")
else:
    st.write(f"優先度 **{min_score}** 以上の激ヤバ課題: **{len(tasks)}** 問")
    
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
                # 危険度表示
                if task["score"] >= 80:
                    st.error(f"🚨 優先度: {task['score']} (至急！)")
                else:
                    st.warning(f"⚠️ 優先度: {task['score']}")
                
                st.subheader(task["name"])
                
                # 進捗
                if task["lv2"]: check_col = COL_LV3 + 1
                elif task["lv1"]: check_col = COL_LV2 + 1
                else: check_col = COL_LV1 + 1
                
                # クリアボタン
                if st.button(f"✅ クリア！", key=f"btn_{task['index']}"):
                    sheet.update_cell(task["index"], check_col, True)
                    st.toast(f"完了！")
                    import time
                    time.sleep(1)
                    st.rerun()

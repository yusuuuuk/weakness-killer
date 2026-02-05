import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date

# ==========================================
# ⚙️ 設定エリア
# ==========================================

# スプレッドシートの「列番号」の設定（A列=0, B列=1, C列=2...）
COL_Q_NUM   = 3  # D列: 問題番号
COL_IMG_URL = 9
COL_LV1     = 5  # F列: 1回目 (Lv1)
COL_LV2     = 6  # G列: 2回目 (Lv2)
COL_LV3     = 7  # H列: 3回目 (Lv3)
COL_SCORE   = 8  # I列: スコア（大きいほど優先）

# ==========================================

# --- 1. アプリ設定 & 認証 ---
st.set_page_config(page_title="Weakness Killer", page_icon="🔥")
st.title("🔥 Weakness Killer (算数)")

# Google Sheetsへの接続
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

try:
    # Secretsから認証情報を読み込む
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # スプレッドシートを開く
    sheet_url = st.secrets["spreadsheet"]["url"]
    worksheet_name = st.secrets["spreadsheet"]["worksheet_name"]
    sheet = client.open_by_url(sheet_url).worksheet(worksheet_name)
    
except Exception as e:
    st.error(f"認証エラー: {e}")
    st.info("Secretsの worksheet_name が正しいか確認してください")
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
    if not isinstance(url, str):
        return None
    if "drive.google.com" in url and "id=" in url:
        try:
            file_id = url.split('id=')[1].split('&')[0]
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
        except:
            return url
    elif "drive.google.com" in url and "/d/" in url:
        try:
            file_id = url.split('/d/')[1].split('/')[0]
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
        except:
            return url
    return url

# --- 3. メイン処理 ---
df = get_data()

if df.empty:
    st.warning("データがありません。")
    st.stop()

tasks = []

# 行ごとにデータを処理
for i, row in df.iterrows():
    try:
        # 列数チェック
        if len(row) <= max(COL_Q_NUM, COL_IMG_URL, COL_SCORE):
            continue

        # データの取得
        q_num = row[COL_Q_NUM]
        raw_url = row[COL_IMG_URL]
        
        # 画像URL変換
        if str(raw_url).startswith("http"):
            img_url = convert_drive_url(raw_url)
        else:
            img_url = None

        # チェックボックスの状態確認
        lv1 = str(row[COL_LV1]).upper() == "TRUE"
        lv2 = str(row[COL_LV2]).upper() == "TRUE"
        lv3 = str(row[COL_LV3]).upper() == "TRUE"
        
        # スコア（優先度）の取得
        # 日付計算ではなく、シートに入っている数字をそのまま使う
        raw_score = row[COL_SCORE]
        score = 0 # 初期値
        
        try:
            # 数値に変換できればそのままスコアにする
            score = int(float(raw_score))
        except:
            # 数値じゃない（空欄や文字）場合は0扱い
            score = 0

        # 表示条件: Lv3(卒業)が未完了であればリストに入れる
        if not lv3:
            tasks.append({
                "index": i + 2, # スプレッドシートの行番号
                "name": q_num,
                "img": img_url,
                "score": score, # 取得したスコアをそのまま使用
                "lv1": lv1, "lv2": lv2, "lv3": lv3
            })

    except Exception as e:
        continue

# 並び替え（スコアが高い順 ＝ 大きい方が優先）
tasks = sorted(tasks, key=lambda x: x["score"], reverse=True)

# --- 4. 画面表示 ---
if not tasks:
    st.balloons()
    st.success("🎉 今日のクエストは全て完了しています！")
else:
    st.write(f"あと **{len(tasks)}** 問の弱点が残っています。")
    
    for task in tasks:
        with st.container():
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            
            with c1:
                if task["img"]:
                    st.image(task["img"], use_container_width=True)
                else:
                    st.warning("📷 画像なし")
            
            with c2:
                # 危険度表示（スコアが高いほど危険）
                score_val = task["score"]
                if score_val >= 100: # 基準はお好みで調整してください
                    st.error(f"🚨 優先度: {score_val} (至急！)")
                elif score_val >= 50:
                    st.warning(f"⚠️ 優先度: {score_val}")
                else:
                    st.info(f"🟢 優先度: {score_val}")
                
                st.subheader(task["name"])
                
                # 進捗ステータス
                if task["lv2"]:
                    status = "最終段階 (Lv3へ挑戦)"
                    check_col = COL_LV3 + 1
                elif task["lv1"]:
                    status = "定着確認 (Lv2へ挑戦)"
                    check_col = COL_LV2 + 1
                else:
                    status = "初回 (Lv1へ挑戦)"
                    check_col = COL_LV1 + 1
                
                st.caption(f"Next: {status}")
                
                # クリアボタン
                if st.button(f"✅ クリア！", key=f"btn_{task['index']}"):
                    sheet.update_cell(task["index"], check_col, True)
                    st.toast(f"『{task['name']}』をクリアしました！")
                    import time
                    time.sleep(1)
                    st.rerun()

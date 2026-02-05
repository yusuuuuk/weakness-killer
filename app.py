import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# ==========================================
# ⚙️ 設定エリア（列番号の定義）
# ==========================================

# 📥 読み込み用（Pandasは0始まり: A=0, B=1, C=2...）
COL_Q_NUM   = 2  # C列: 問題名
COL_IMG_URL = 9  # J列: 画像URL（作業用列）
COL_SCORE   = 8  # I列: スコア

# 🔘 チェックボックス判定用（読み込み用）
COL_LV1_IDX = 5  # F列
COL_LV2_IDX = 6  # G列
COL_LV3_IDX = 7  # H列

# 📤 書き込み用（Gspreadは1始まり: A=1, B=2, C=3...）
# ※ここを間違えるとズレるので注意！
WRITE_COL_DATE = 4  # D列: 前回実施日（ここを更新します）
WRITE_COL_LV1  = 6  # F列: Lv1チェック
WRITE_COL_LV2  = 7  # G列: Lv2チェック
WRITE_COL_LV3  = 8  # H列: Lv3チェック

# ==========================================

# --- 1. アプリ設定 ---
st.set_page_config(page_title="Weakness Killer", page_icon="🔥")
st.title("🔥 Weakness Killer (算数)")

# サイドバー（フィルタ）
with st.sidebar:
    st.header("🔍 表示フィルタ")
    # デフォルト80（高いものだけ表示）
    min_score = st.slider("最低優先度", 0, 200, 80)
    st.caption(f"スコア {min_score} 以上の問題を表示中")
    st.info("💡 ヒント: スコアが高いほど「忘れている」危険な問題です。")

# --- 2. Google Sheets 接続 ---
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

# --- 3. データ処理関数 ---
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

# --- 4. メインロジック ---
df = get_data()
tasks = []

# データ解析
for i, row in df.iterrows():
    try:
        # 列数不足のエラー回避
        if len(row) <= max(COL_Q_NUM, COL_IMG_URL, COL_SCORE, COL_LV3_IDX): continue

        q_num = row[COL_Q_NUM]
        raw_url = row[COL_IMG_URL]
        img_url = convert_drive_url(raw_url) if str(raw_url).startswith("http") else None

        # スコア取得
        try: score = int(float(row[COL_SCORE]))
        except: score = 0

        # チェックボックス状態
        lv1 = str(row[COL_LV1_IDX]).upper() == "TRUE"
        lv2 = str(row[COL_LV2_IDX]).upper() == "TRUE"
        lv3 = str(row[COL_LV3_IDX]).upper() == "TRUE"

        # リスト追加条件: 卒業(Lv3)していない & スコア基準以上
        if not lv3 and score >= min_score:
            tasks.append({
                "index": i + 2, # 行番号(header+1)
                "name": q_num,
                "img": img_url,
                "score": score,
                "lv1": lv1, "lv2": lv2, "lv3": lv3
            })
    except: continue

# 優先度順に並び替え
tasks = sorted(tasks, key=lambda x: x["score"], reverse=True)

# --- 5. 画面表示 ---
if not tasks:
    st.balloons()
    st.success(f"🎉 優先度 {min_score} 以上の課題は全て完了！完璧です！")
    if min_score > 0:
        st.caption("サイドバーのスライダーを下げると、隠れている課題が見つかるかも…？")
else:
    st.write(f"優先度 **{min_score}** 以上の課題: **{len(tasks)}** 問")
    st.caption("自己評価に合わせてボタンを選んでください。スケジュールが自動調整されます。")
    
    for task in tasks:
        with st.container():
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            
            # --- 左カラム: 画像 ---
            with c1:
                if task["img"]:
                    st.image(task["img"], use_container_width=True)
                else:
                    st.warning("📷 画像なし")
                    st.caption("スプレッドシートのURLを確認")
            
            # --- 右カラム: 操作 ---
            with c2:
                # 危険度バッジ
                if task["score"] >= 100:
                    st.error(f"🚨 優先度: {task['score']} (危険域)")
                elif task["score"] >= 50:
                    st.warning(f"⚠️ 優先度: {task['score']} (要復習)")
                else:
                    st.info(f"🟢 優先度: {task['score']}")
                
                st.subheader(task["name"])
                
                # 次のステップ判定
                if task["lv2"]:
                    current_stage = "Lv3 (最終仕上げ)"
                    target_check_col = WRITE_COL_LV3
                elif task["lv1"]:
                    current_stage = "Lv2 (定着確認)"
                    target_check_col = WRITE_COL_LV2
                else:
                    current_stage = "Lv1 (初挑戦)"
                    target_check_col = WRITE_COL_LV1
                
                st.caption(f"Current Stage: **{current_stage}**")
                
                # ==========================================
                # 🎮 3段階評価ボタン
                # ==========================================
                st.write("▼ 今日の手応えは？")
                b1, b2, b3 = st.columns(3)
                
                today_str = datetime.now().strftime('%Y/%m/%d')

                # 🟢 余裕 (Next Level)
                with b1:
                    if st.button("🟢 余裕!", key=f"ok_{task['index']}"):
                        # 1. チェックを入れて進級
                        sheet.update_cell(task["index"], target_check_col, True)
                        # 2. 日付更新
                        sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                        
                        st.balloons()
                        st.toast("素晴らしい！次のレベルへ進みます🚀")
                        time.sleep(1)
                        st.rerun()

                # 🟡 微妙 (Stay)
                with b2:
                    if st.button("🟡 微妙...", key=f"soso_{task['index']}"):
                        # チェックは入れない（ステイ）
                        # 日付だけ更新してリセット
                        sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                        
                        st.toast("OK！同じレベルでもう一度やりましょう💪")
                        time.sleep(1)
                        st.rerun()

                # 🔴 敗北 (Stay)
                with b3:
                    if st.button("🔴 敗北", key=f"bad_{task['index']}"):
                        # チェック入れない
                        # 日付だけ更新
                        sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                        
                        st.error("ドンマイ！明日リベンジです🔥")
                        time.sleep(1)
                        st.rerun()

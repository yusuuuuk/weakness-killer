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
COL_Q_NUM   = 2  # C列: 問題名（※表示はしませんが内部管理用に使います）
COL_LAST_DATE = 3 # D列: 前回実施日（ここを表示に使います）
COL_IMG_URL = 9  # J列: 画像URL（作業用列）
COL_SCORE   = 8  # I列: スコア

# 🔘 チェックボックス判定用（読み込み用）
COL_LV1_IDX = 5  # F列
COL_LV2_IDX = 6  # G列
COL_LV3_IDX = 7  # H列

# 📤 書き込み用（Gspreadは1始まり: A=1, B=2, C=3...）
WRITE_COL_DATE = 4  # D列: 前回実施日（ここを更新します）
WRITE_COL_LV1  = 6  # F列: Lv1チェック
WRITE_COL_LV2  = 7  # G列: Lv2チェック
WRITE_COL_LV3  = 8  # H列: Lv3チェック

# ==========================================

# --- 1. アプリ設定 & CSSデザイン ---
st.set_page_config(page_title="Weakness Killer", page_icon="🔥", layout="centered")

# カスタムCSS（カードデザイン用）
st.markdown("""
<style>
    /* 全体の背景 */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* カードのデザイン */
    .task-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #f1f5f9;
        margin-bottom: 24px;
    }
    
    /* 日付表示（文字サイズUP） */
    .task-date {
        font-size: 18px; /* 14px -> 18px */
        font-weight: 600;
        color: #475569;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
    }
    
    /* バッジ共通（文字サイズUP） */
    .badge {
        display: inline-block;
        padding: 6px 16px; /* 余白も大きく */
        border-radius: 9999px;
        font-size: 16px; /* 12px -> 16px */
        font-weight: 700;
        margin-right: 8px;
        margin-bottom: 12px;
    }
    
    /* 優先度バッジの色 */
    .badge-danger { background-color: #fef2f2; color: #ef4444; border: 1px solid #fecaca; }
    .badge-warning { background-color: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
    .badge-info { background-color: #eff6ff; color: #3b82f6; border: 1px solid #bfdbfe; }

    /* ステータス表示（文字サイズUP・強調） */
    .status-label {
        font-size: 20px; /* 14px -> 20px */
        font-weight: 700;
        color: #059669;
        margin-bottom: 24px; /* ボタンとの距離を少し空ける */
        background-color: #ecfdf5;
        padding: 8px 12px;
        border-radius: 8px;
        display: inline-block;
    }
    
    /* 画像エリア */
    .img-container {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

st.title("🔥 Weakness Killer (算数)")

# サイドバー
with st.sidebar:
    st.header("🔍 表示フィルタ")
    min_score = st.slider("最低優先度", 0, 200, 80)
    st.caption(f"スコア {min_score} 以上の問題を表示中")

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

for i, row in df.iterrows():
    try:
        # 列数チェック
        if len(row) <= max(COL_Q_NUM, COL_LAST_DATE, COL_IMG_URL, COL_SCORE, COL_LV3_IDX): continue

        q_num = row[COL_Q_NUM]     # 問題名 (C列)
        last_date = row[COL_LAST_DATE] # 前回実施日 (D列)
        raw_url = row[COL_IMG_URL] # 画像URL (J列)
        img_url = convert_drive_url(raw_url) if str(raw_url).startswith("http") else None

        try: score = int(float(row[COL_SCORE]))
        except: score = 0

        lv1 = str(row[COL_LV1_IDX]).upper() == "TRUE"
        lv2 = str(row[COL_LV2_IDX]).upper() == "TRUE"
        lv3 = str(row[COL_LV3_IDX]).upper() == "TRUE"

        # リスト追加条件
        if not lv3 and score >= min_score:
            tasks.append({
                "index": i + 2,
                "name": q_num,
                "date": last_date,
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
else:
    st.markdown(f"##### 優先度 {min_score} 以上の課題: {len(tasks)} 問")
    
    for task in tasks:
        # カードコンテナの開始
        st.markdown('<div class="task-card">', unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 1.5])
        
        # --- 左カラム: 画像 ---
        with c1:
            if task["img"]:
                st.markdown(f'<div class="img-container"><img src="{task["img"]}" style="width:100%"></div>', unsafe_allow_html=True)
            else:
                st.warning("📷 画像なし")

        # --- 右カラム: 情報 & 操作 ---
        with c2:
            # 1. バッジ表示 (優先度) - 文字サイズUP
            if task["score"] >= 100:
                badge_html = f'<span class="badge badge-danger">🚨 優先度: {task["score"]}</span>'
            elif task["score"] >= 50:
                badge_html = f'<span class="badge badge-warning">⚠️ 優先度: {task["score"]}</span>'
            else:
                badge_html = f'<span class="badge badge-info">🟢 優先度: {task["score"]}</span>'
            
            st.markdown(badge_html, unsafe_allow_html=True)

            # 2. 日付表示 (名前を削除し、日付を強調)
            st.markdown(f'<div class="task-date">📅 前回: {task["date"]}</div>', unsafe_allow_html=True)

            # 3. 進捗ステータス判定
            if task["lv2"]:
                current_stage = "Lv3 (最終仕上げ)"
                target_check_col = WRITE_COL_LV3
            elif task["lv1"]:
                current_stage = "Lv2 (定着確認)"
                target_check_col = WRITE_COL_LV2
            else:
                current_stage = "Lv1 (初挑戦)"
                target_check_col = WRITE_COL_LV1
            
            # Next Step表示 - 文字サイズUP & 強調
            st.markdown(f'<div class="status-label">Next Step: {current_stage}</div>', unsafe_allow_html=True)

            # 4. 3段階評価ボタン
            b1, b2, b3 = st.columns(3)
            today_str = datetime.now().strftime('%Y/%m/%d')

            with b1:
                if st.button("🟢 余裕", key=f"ok_{task['index']}", use_container_width=True):
                    sheet.update_cell(task["index"], target_check_col, True)
                    sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                    st.toast("Nice! 次のレベルへ🚀")
                    time.sleep(1)
                    st.rerun()

            with b2:
                if st.button("🟡 微妙", key=f"soso_{task['index']}", use_container_width=True):
                    sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                    st.toast("OK! 反復練習しましょう💪")
                    time.sleep(1)
                    st.rerun()

            with b3:
                if st.button("🔴 敗北", key=f"bad_{task['index']}", use_container_width=True):
                    sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                    st.toast("Don't worry! 明日また出題します🔥")
                    time.sleep(1)
                    st.rerun()
        
        # カードコンテナの終了
        st.markdown('</div>', unsafe_allow_html=True)

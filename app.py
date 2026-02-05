import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# ==========================================
# ⚙️ 設定エリア
# ==========================================
COL_Q_NUM   = 2  # C列: 問題名
COL_LAST_DATE = 3 # D列: 前回実施日
COL_IMG_URL = 9  # J列: 画像URL
COL_SCORE   = 8  # I列: スコア

COL_LV1_IDX = 5  # F列
COL_LV2_IDX = 6  # G列
COL_LV3_IDX = 7  # H列

WRITE_COL_DATE = 4  # D列: 更新用
WRITE_COL_LV1  = 6  # F列: 更新用
WRITE_COL_LV2  = 7  # G列: 更新用
WRITE_COL_LV3  = 8  # H列: 更新用

# ==========================================
# 🎨 デザイン設定 & CSS
# ==========================================
st.set_page_config(page_title="Weakness Killer", page_icon="🔥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    .stApp {
        background-color: #f1f5f9; /* Slate-100 */
        font-family: 'Inter', sans-serif;
    }

    /* --- メトリクスエリア --- */
    .metric-container {
        background: white;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
        border: 1px solid #e2e8f0;
    }
    .metric-label { font-size: 14px; color: #64748b; font-weight: 600; }
    .metric-value { font-size: 28px; color: #0f172a; font-weight: 800; }
    .metric-value.danger { color: #ef4444; }

    /* --- カード本体 --- */
    .task-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 0; /* 内部でpadding調整 */
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        margin-bottom: 30px;
        border: 1px solid #e2e8f0;
        overflow: hidden;
        transition: transform 0.2s;
    }
    .task-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    }

    /* --- カードヘッダー（優先度バー） --- */
    .card-header-bar {
        height: 8px;
        width: 100%;
    }

    /* --- コンテンツエリア --- */
    .card-content {
        padding: 24px;
    }

    /* --- 画像スタイル --- */
    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100%;
        background-color: #f8fafc; /* 画像背景色を追加 */
        border-radius: 8px;
    }
    
    div[data-testid="stImage"] img {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        object-fit: contain;
        max-height: 400px; /* ★修正: 高さをさらに緩和 */
        width: auto !important;
        max-width: 100%;
    }

    /* --- 情報ラベル --- */
    .info-label {
        font-size: 13px;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .date-text {
        font-size: 16px;
        color: #334155;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* --- プログレスバー --- */
    .progress-track {
        background-color: #f1f5f9;
        height: 10px;
        border-radius: 999px;
        margin: 12px 0 20px 0;
        overflow: hidden;
        position: relative;
    }
    .progress-fill {
        height: 100%;
        border-radius: 999px;
        transition: width 0.5s ease;
    }
    
    .stage-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 800;
        color: white;
        margin-bottom: 12px;
    }

</style>
""", unsafe_allow_html=True)

# --- Google Sheets 接続 ---
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

# --- 関数 ---
def get_data():
    all_values = sheet.get_all_values()
    if len(all_values) < 2: return pd.DataFrame()
    return pd.DataFrame(all_values[1:], columns=all_values[0])

def convert_drive_url(url):
    """
    GoogleドライブのURLを直リンク(lh3.googleusercontent.com)に変換する
    ※この形式はiPhone/Safariでの表示トラブルが最も少ないです
    """
    if not isinstance(url, str): return None
    
    file_id = None
    if "drive.google.com" in url and "id=" in url:
        try: file_id = url.split('id=')[1].split('&')[0]
        except: pass
    elif "drive.google.com" in url and "/d/" in url:
        try: file_id = url.split('/d/')[1].split('/')[0]
        except: pass
        
    if file_id:
        # ★修正: lh3形式に変更 (サイズ指定なし=最大サイズ)
        return f"https://lh3.googleusercontent.com/d/{file_id}"
        
    return url

# --- データ処理 ---
df = get_data()
tasks = []

# サイドバーフィルタ
with st.sidebar:
    st.header("⚙️ 設定")
    min_score = st.slider("最低優先度", 0, 200, 80)
    st.info("💡 iPhoneで画像が表示されない場合、Googleドライブのフォルダ共有設定を「リンクを知っている全員」に変更してください。")

for i, row in df.iterrows():
    try:
        if len(row) <= max(COL_Q_NUM, COL_LAST_DATE, COL_IMG_URL, COL_SCORE, COL_LV3_IDX): continue

        q_num = row[COL_Q_NUM]
        last_date = row[COL_LAST_DATE]
        raw_url = row[COL_IMG_URL]
        img_url = convert_drive_url(raw_url) if str(raw_url).startswith("http") else None
        
        try: score = int(float(row[COL_SCORE]))
        except: score = 0
        
        lv1 = str(row[COL_LV1_IDX]).upper() == "TRUE"
        lv2 = str(row[COL_LV2_IDX]).upper() == "TRUE"
        lv3 = str(row[COL_LV3_IDX]).upper() == "TRUE"

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

tasks = sorted(tasks, key=lambda x: x["score"], reverse=True)

# ==========================================
# 🖥️ メインUI構築
# ==========================================

# 1. ヘッダーエリア
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    st.title("🔥 Weakness Killer")
    st.caption("Strategic Learning Management System")

# メトリクス表示
total_tasks = len(tasks)
high_priority = sum(1 for t in tasks if t["score"] >= 100)

with c2:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">REMAINING TASKS</div>
        <div class="metric-value">{total_tasks}</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">HIGH PRIORITY</div>
        <div class="metric-value danger">{high_priority}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# 2. タスクリスト
if not tasks:
    st.balloons()
    st.success("🎉 All weaknesses eliminated! Great job!")
else:
    for task in tasks:
        # ステータス判定
        if task["lv2"]:
            stage_name = "Lv3: Final Check"
            stage_color = "#3b82f6" # Blue
            progress_pct = "66%"
            target_check_col = WRITE_COL_LV3
        elif task["lv1"]:
            stage_name = "Lv2: Review"
            stage_color = "#8b5cf6" # Purple
            progress_pct = "33%"
            target_check_col = WRITE_COL_LV2
        else:
            stage_name = "Lv1: First Try"
            stage_color = "#10b981" # Green
            progress_pct = "5%"
            target_check_col = WRITE_COL_LV1
            
        # 優先度判定
        if task["score"] >= 100:
            border_color = "#ef4444" # Red
        elif task["score"] >= 50:
            border_color = "#f59e0b" # Orange
        else:
            border_color = "#10b981" # Green

        # --- カード開始 ---
        st.markdown(f"""<div class="task-card">
            <div class="card-header-bar" style="background-color: {border_color};"></div>
            <div class="card-content">""", unsafe_allow_html=True)

        # ★ 修正: カラム比率を [1, 1.5] に拡大しました
        col_img, col_info = st.columns([1, 1.5])

        # 左: 画像
        with col_img:
            if task["img"]:
                # Streamlit標準関数を使用
                st.image(task["img"]) 
            else:
                st.warning("No Image")

        # 右: 情報
        with col_info:
            # Stage Badge
            st.markdown(f"""
            <div class="stage-badge" style="background-color: {stage_color};">
                {stage_name}
            </div>
            """, unsafe_allow_html=True)

            # 前回実施日
            display_date = task["date"] if task["date"] else "🆕 初挑戦"
            st.markdown(f"""
            <div class="info-label">LAST REVIEWED</div>
            <div class="date-text">📅 {display_date}</div>
            """, unsafe_allow_html=True)

            # プログレスバー
            st.markdown(f"""
            <div class="progress-track">
                <div class="progress-fill" style="width: {progress_pct}; background-color: {stage_color};"></div>
            </div>
            """, unsafe_allow_html=True)

            # アクションボタン
            st.markdown('<div class="info-label">SELF EVALUATION</div>', unsafe_allow_html=True)
            b1, b2, b3 = st.columns(3)
            
            today_str = datetime.now().strftime('%Y/%m/%d')
            
            with b1:
                if st.button("🟢 余裕", key=f"easy_{task['index']}", use_container_width=True):
                    sheet.update_cell(task["index"], target_check_col, True)
                    sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                    st.toast("Level Up! 🚀")
                    time.sleep(1)
                    st.rerun()
            with b2:
                if st.button("🟡 微妙", key=f"soso_{task['index']}", use_container_width=True):
                    sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                    st.toast("Review scheduled! 💪")
                    time.sleep(1)
                    st.rerun()
            with b3:
                if st.button("🔴 敗北", key=f"bad_{task['index']}", use_container_width=True):
                    sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                    st.toast("Don't worry, try again tomorrow! 🔥")
                    time.sleep(1)
                    st.rerun()

        # --- カード終了 ---
        st.markdown('</div></div>', unsafe_allow_html=True)

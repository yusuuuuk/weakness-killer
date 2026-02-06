import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import time

# ==========================================
# ⚙️ 設定エリア
# ==========================================
# ※タブを分けるため、COL_STUDENT（A列の名前チェック）は不要になります
COL_Q_NUM     = 2  # C列: 問題名
COL_LAST_DATE = 3  # D列: 前回実施日
COL_IMG_URL   = 9  # J列: 画像URL
COL_SCORE     = 8  # I列: スコア

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
st.set_page_config(page_title="Personal Learning Tracker", page_icon="🎯", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&family=Zen+Maru+Gothic:wght@700;900&display=swap');
    
    .stApp {
        background-color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1 {
        font-family: 'Zen Maru Gothic', sans-serif;
        font-size: 36px !important;
        font-weight: 900 !important;
        letter-spacing: -2px !important;
        color: #0f172a !important;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }

    .metric-container {
        background: white;
        padding: 12px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
        border: 1px solid #e2e8f0;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-label { 
        font-size: 15px; 
        color: #64748b; 
        font-weight: 700; 
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .metric-value { 
        font-size: 20px; 
        color: #0f172a; 
        font-weight: 800; 
        line-height: 1.2;
    }
    .metric-value.danger { color: #ef4444; }
    .metric-value.success { color: #10b981; }
    .metric-value.info { color: #3b82f6; }

    .task-card {
        background-color: #ffffff;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
        border: 1px solid #e2e8f0;
        overflow: hidden;
        height: 100%;
    }

    .card-header-bar {
        height: 6px;
        width: 100%;
    }

    .card-content {
        padding: 16px;
    }

    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
        align-items: flex-start;
        height: 100%;
        min-height: auto;
    }
    
    div[data-testid="stImage"] img {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        object-fit: contain;
        max-height: 500px; 
        width: auto !important;
        max-width: 100%;
    }

    p, h2, h3 { margin-bottom: 0px !important; }

    .info-label {
        font-size: 15px;
        color: #94a3b8;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 8px;
        margin-bottom: 2px;
    }
    .date-text {
        font-size: 20px;
        color: #334155;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .stage-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 15px;
        font-weight: 800;
        color: white;
        margin-bottom: 4px;
    }

    .progress-track {
        background-color: #f1f5f9;
        height: 6px;
        border-radius: 999px;
        margin: 8px 0 16px 0;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        border-radius: 999px;
    }
    
    .stButton button {
        margin-bottom: 4px;
    }

    div[data-testid="stToast"] {
        background-color: #ffffff !important;
        border: 2px solid #3b82f6 !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1) !important;
        opacity: 1 !important;
        padding: 16px 20px !important;
        border-radius: 12px !important;
        max-width: 450px !important;
        width: auto !important;
        height: auto !important;
        min-height: 80px !important;
        display: flex !important;
        align-items: flex-start !important;
        overflow: visible !important;
    }
    
    div[data-testid="stToast"] [data-testid="stToastIcon"] {
        font-size: 24px !important;
        line-height: 1.2 !important;
        margin-right: 14px !important;
        flex-shrink: 0 !important;
    }

    div[data-testid="stToast"] [data-testid="stMarkdownContainer"] p {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #1e293b !important;
        line-height: 1.5 !important; 
        margin: 0 !important;
        padding: 0 !important;
        white-space: normal !important;
    }

    @media only screen and (max-width: 600px) {
        div[data-testid="stImage"] img { max-height: 500px; }
        [data-testid="column"] { padding: 0 !important; }
        .metric-container { margin-bottom: 8px; }
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Google Sheets 接続準備 ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = dict(st.secrets["gcp_service_account"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet_url = st.secrets["spreadsheet"]["url"]
spreadsheet = client.open_by_url(sheet_url)

# ==========================================
# 👥 認証ロジック (タブ名で判定)
# ==========================================

# 1. URLパラメータから名前を取得
query_params = st.query_params
url_student = query_params.get("student", None)

if "student_name" not in st.session_state:
    st.session_state.student_name = url_student

# 2. ログイン画面
if not st.session_state.student_name:
    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>🎯 Welcome</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>お名前(苗字のみ)を入力してください</p>", unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        input_name = st.text_input("名前", placeholder="例：中村", label_visibility="collapsed")
        if st.button("ログイン", use_container_width=True):
            if input_name:
                # 入力された名前の「タブ」が存在するかチェック
                try:
                    spreadsheet.worksheet(input_name)
                    st.session_state.student_name = input_name
                    st.query_params["student"] = input_name
                    st.rerun()
                except gspread.exceptions.WorksheetNotFound:
                    st.error(f"「{input_name}」さんのシートが見つかりません。")
            else:
                st.warning("お名前を入力してください。")
    st.stop()

# ==========================================
# 📊 データ取得・処理 (ログイン後)
# ==========================================
selected_student = st.session_state.student_name

try:
    # ログインした名前と同じ名前のタブを開く
    sheet = spreadsheet.worksheet(selected_student)
except:
    st.error("エラーが発生しました。もう一度ログインしてください。")
    st.session_state.student_name = None
    st.stop()

def get_data():
    all_values = sheet.get_all_values()
    if len(all_values) < 2: return pd.DataFrame()
    return pd.DataFrame(all_values[1:], columns=all_values[0])

def convert_drive_url(url):
    if not isinstance(url, str): return None
    file_id = None
    if "drive.google.com" in url and "id=" in url:
        try: file_id = url.split('id=')[1].split('&')[0]
        except: pass
    elif "drive.google.com" in url and "/d/" in url:
        try: file_id = url.split('/d/')[1].split('/')[0]
        except: pass
    if file_id: return f"https://lh3.googleusercontent.com/d/{file_id}"
    return url

df = get_data()

# 共通変数の準備
tasks = []
stats = { "total_active": 0, "graduated": 0 }

JST_OFFSET = timedelta(hours=9)
today_dt = datetime.utcnow() + JST_OFFSET
today_date = today_dt.date()
today_str = today_dt.strftime('%Y/%m/%d')
tomorrow_str = (today_dt + timedelta(days=1)).strftime('%Y/%m/%d')

# サイドバー設定
with st.sidebar:
    st.header("👤 Account")
    st.info(f"ログイン: {selected_student}")
    if st.button("ログアウト"):
        st.session_state.student_name = None
        st.query_params.clear()
        st.rerun()
    st.markdown("---")
    st.header("⚙️ Settings")
    min_score = st.slider("最低優先度", 0, 100, 70)

# タブ内の全データを処理 (生徒名フィルタは不要)
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

        if lv3: stats["graduated"] += 1
        else: stats["total_active"] += 1

        is_today_done = False
        if last_date:
            try:
                if len(last_date.split('/')) == 3: ld_obj = datetime.strptime(last_date, '%Y/%m/%d').date()
                elif len(last_date.split('/')) == 2: ld_obj = datetime.strptime(last_date, '%m/%d').date().replace(year=today_date.year)
                else: ld_obj = None
                if ld_obj == today_date: is_today_done = True
            except: pass

        if not lv3 and score >= min_score and not is_today_done:
            tasks.append({
                "index": i + 2, "name": q_num, "date": last_date, "img": img_url,
                "score": score, "lv1": lv1, "lv2": lv2, "lv3": lv3
            })
    except: continue

tasks = sorted(tasks, key=lambda x: x["score"], reverse=True)

# ==========================================
# メインUI構築
# ==========================================
st.markdown(f"""
    <h1 style='font-family: "Zen Maru Gothic", sans-serif; font-weight: 900; font-size: 36px; color: #0f172a; margin-bottom: 0;'>
        🎯 {selected_student}さんの学習サポート
    </h1>
""", unsafe_allow_html=True)
st.caption(f"Hello, {selected_student}! 今日の弱点を克服しましょう。")

with st.expander("💡 評価のめやす"):
    st.markdown("""
    - **🟢 余裕** ： 見た瞬間に解法が浮かび、迷わず解けた！ 
    - **🟡 微妙** ： 解けたけど時間がかかった。少し自信がない。 
    - **🔴 敗北** ： 解き方がわからなかった。間違えてしまった。 
    """, unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
with m1: st.markdown(f"""<div class="metric-container"><div class="metric-label">🔥 今日の課題</div><div class="metric-value">{len(tasks)}</div></div>""", unsafe_allow_html=True)
high_priority_count = sum(1 for t in tasks if t["score"] >= 100)
with m2: st.markdown(f"""<div class="metric-container"><div class="metric-label">🚨 最優先</div><div class="metric-value danger">{high_priority_count}</div></div>""", unsafe_allow_html=True)
with m3: st.markdown(f"""<div class="metric-container"><div class="metric-label">🎓 達成</div><div class="metric-value success">{stats['graduated']}</div></div>""", unsafe_allow_html=True)

st.markdown("---")

if not tasks:
    st.balloons()
    st.success(f"🎉 {selected_student}さん、今日の優先タスクはすべて完了です！")
else:
    rows = [tasks[i:i + 2] for i in range(0, len(tasks), 2)]
    for row in rows:
        cols = st.columns(2)
        for idx, task in enumerate(row):
            with cols[idx]:
                if task["lv2"]: stage_name, stage_color, progress_pct, target_check_col = "Lv3", "#3b82f6", "66%", WRITE_COL_LV3
                elif task["lv1"]: stage_name, stage_color, progress_pct, target_check_col = "Lv2", "#8b5cf6", "33%", WRITE_COL_LV2
                else: stage_name, stage_color, progress_pct, target_check_col = "Lv1", "#10b981", "5%", WRITE_COL_LV1
                    
                if task["score"] >= 100: border_color = "#ef4444"
                elif task["score"] >= 50: border_color = "#f59e0b"
                else: border_color = "#10b981"

                st.markdown(f"""<div class="task-card"><div class="card-header-bar" style="background-color: {border_color};"></div><div class="card-content">""", unsafe_allow_html=True)
                c_img, c_info = st.columns([1, 1])
                with c_img:
                    if task["img"]: st.image(task["img"])
                    else: st.warning("No Image")
                with c_info:
                    st.markdown(f"""<div class="stage-badge" style="background-color: {stage_color};">{stage_name}</div>""", unsafe_allow_html=True)
                    display_date = task["date"] if task["date"] else "🆕 初挑戦"
                    st.markdown(f"""<div class="info-label" style="margin-top:0;">LAST REVIEWED</div><div class="date-text">📅 {display_date}</div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="progress-track"><div class="progress-fill" style="width: {progress_pct}; background-color: {stage_color};"></div></div>""", unsafe_allow_html=True)
                    
                    if st.button("🟢 余裕", key=f"easy_{task['index']}", use_container_width=True):
                        sheet.update_cell(task["index"], target_check_col, True)
                        sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                        st.toast(f"ナイス！出題間隔をあけます🚀", icon="🎉")
                        time.sleep(1); st.rerun()
                    if st.button("🟡 微妙", key=f"soso_{task['index']}", use_container_width=True):
                        sheet.update_cell(task["index"], WRITE_COL_DATE, tomorrow_str if stage_name=="Lv1" else today_str)
                        st.toast("OK！忘れないうちにまた復習しましょう💪", icon="🔄")
                        time.sleep(1); st.rerun()
                    if st.button("🔴 敗北", key=f"bad_{task['index']}", use_container_width=True):
                        sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                        if task["lv2"]: sheet.update_cell(task["index"], WRITE_COL_LV2, "FALSE")
                        elif task["lv1"]: sheet.update_cell(task["index"], WRITE_COL_LV1, "FALSE")
                        st.toast("ドンマイ！明日またリベンジしましょう🔥", icon="📉")
                        time.sleep(1); st.rerun()
                st.markdown('</div></div>', unsafe_allow_html=True)

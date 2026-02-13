import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import time

# ==========================================
# ⚙️ Configuration Area
# ==========================================
COL_Q_NUM     = 2  # Column C: Question Name
COL_LAST_DATE = 3  # Column D: Last Reviewed Date
COL_IMG_URL   = 9  # Column J: Image URL
COL_SCORE     = 8  # Column I: Priority Score

COL_LV1_IDX = 5  # Column F
COL_LV2_IDX = 6  # Column G
COL_LV3_IDX = 7  # Column H

WRITE_COL_DATE = 4  # Column D: Update Date
WRITE_COL_LV1  = 6  # Column F: Update Lv1
WRITE_COL_LV2  = 7  # Column G: Update Lv2
WRITE_COL_LV3  = 8  # Column H: Update Lv3

# ==========================================
# 🎨 Design & CSS
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
        font-size: 32px !important;
        font-weight: 900 !important;
        letter-spacing: -1px !important;
        color: #0f172a !important;
        margin-bottom: 0px !important;
    }

    /* Header area with student name and switch button */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
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
        font-size: 14px; 
        color: #64748b; 
        font-weight: 700; 
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .metric-value { 
        font-size: 20px; 
        color: #0f172a; 
        font-weight: 800; 
    }
    .metric-value.danger { color: #ef4444; }
    .metric-value.success { color: #10b981; }

    .task-card {
        background-color: #ffffff;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
        border: 1px solid #e2e8f0;
        overflow: hidden;
        height: 100%;
    }

    .card-header-bar { height: 6px; width: 100%; }
    .card-content { padding: 16px; }

    div[data-testid="stImage"] img {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        object-fit: contain;
        max-height: 450px; 
        width: auto !important;
    }

    .stage-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 800;
        color: white;
        margin-bottom: 8px;
    }

    .info-label { font-size: 13px; color: #94a3b8; font-weight: 700; margin-top: 8px; }
    .date-text { font-size: 18px; color: #334155; font-weight: 700; }

    /* Toast notification styling */
    div[data-testid="stToast"] {
        background-color: #ffffff !important;
        border: 2px solid #3b82f6 !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1) !important;
        padding: 16px !important;
        border-radius: 12px !important;
        height: auto !important;
        min-height: 80px !important;
    }

    @media only screen and (max-width: 600px) {
        h1 { font-size: 24px !important; }
        .metric-container { margin-bottom: 8px; }
    }
    
    #MainMenu, footer, header, [data-testid="stToolbar"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Google Sheets Connection ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_dict = dict(st.secrets["gcp_service_account"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet_url = st.secrets["spreadsheet"]["url"]
spreadsheet = client.open_by_url(sheet_url)

# ==========================================
# 👥 Auth & Navigation Logic
# ==========================================

# Function to logout/return to login screen
def handle_logout():
    st.session_state.student_name = None
    st.query_params.clear()
    st.rerun()

# 1. Get name from URL or Session
query_params = st.query_params
url_student = query_params.get("student", None)

if "student_name" not in st.session_state:
    st.session_state.student_name = url_student

# 2. Login Screen (if no name is set)
if not st.session_state.student_name:
    st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 48px !important;'>🎯 Welcome</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 18px;'>お名前(漢字フルネーム)を入力して開始しましょう</p>", unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([1, 1.5, 1])
    with center_col:
        input_name = st.text_input("名前", placeholder="例：中村友翼", label_visibility="collapsed")
        if st.button("ログインする", use_container_width=True):
            if input_name:
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
# 📊 Data Loading (After Login)
# ==========================================
selected_student = st.session_state.student_name

try:
    sheet = spreadsheet.worksheet(selected_student)
except:
    # Handle error if worksheet is missing or name is invalid
    st.error(f"「{selected_student}」さんのデータにアクセスできませんでした。")
    if st.button("ログイン画面に戻る"):
        handle_logout()
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
tasks = []
stats = { "total_active": 0, "graduated": 0 }

JST = timedelta(hours=9)
today_dt = datetime.utcnow() + JST
today_date = today_dt.date()
today_str = today_dt.strftime('%Y/%m/%d')
tomorrow_str = (today_dt + timedelta(days=1)).strftime('%Y/%m/%d')

# --- Header Section ---
h_left, h_right = st.columns([4, 1])
with h_left:
    st.markdown(f"<h1>🎯 {selected_student} さんの反復学習サポート</h1>", unsafe_allow_html=True)

st.caption(f"Hello、{selected_student}さん。今日も一歩ずつ進んでいきましょう！")

# --- Process Data ---
with st.sidebar:
    st.header("⚙️ Settings")
    min_score = st.slider("最低優先度", 0, 100, 70)
    st.markdown("---")
    st.write("※「戻る」ボタンで別の生徒に切り替えられます。")

for i, row in df.iterrows():
    try:
        if len(row) <= max(COL_Q_NUM, COL_LAST_DATE, COL_IMG_URL, COL_SCORE, COL_LV3_IDX): continue
        q_num, last_date, raw_url = row[COL_Q_NUM], row[COL_LAST_DATE], row[COL_IMG_URL]
        img_url = convert_drive_url(raw_url) if str(raw_url).startswith("http") else None
        try: score = int(float(row[COL_SCORE]))
        except: score = 0
        lv1, lv2, lv3 = [str(row[idx]).upper() == "TRUE" for idx in [COL_LV1_IDX, COL_LV2_IDX, COL_LV3_IDX]]

        if lv3: stats["graduated"] += 1
        else: stats["total_active"] += 1

        is_today_done = False
        if last_date:
            try:
                if len(last_date.split('/')) == 3: ld_obj = datetime.strptime(last_date, '%Y/%m/%d').date()
                elif len(last_date.split('/')) == 2: ld_obj = datetime.strptime(last_date, '%m/%d').date().replace(year=today_date.year)
                else: ld_obj = None
                if ld_obj >= today_date: is_today_done = True
            except: pass

        if not lv3 and score >= min_score and not is_today_done:
            tasks.append({
                "index": i + 2, "name": q_num, "date": last_date, "img": img_url,
                "score": score, "lv1": lv1, "lv2": lv2, "lv3": lv3
            })
    except: continue

tasks = sorted(tasks, key=lambda x: x["score"], reverse=True)

# --- Dashboard ---
m1, m2, m3 = st.columns(3)
with m1: st.markdown(f"""<div class="metric-container"><div class="metric-label">🔥 今日の課題</div><div class="metric-value">{len(tasks)}</div></div>""", unsafe_allow_html=True)
high_priority_count = sum(1 for t in tasks if t["score"] >= 100)
with m2: st.markdown(f"""<div class="metric-container"><div class="metric-label">🚨 最優先</div><div class="metric-value danger">{high_priority_count}</div></div>""", unsafe_allow_html=True)
with m3: st.markdown(f"""<div class="metric-container"><div class="metric-label">🎓 達成</div><div class="metric-value success">{stats['graduated']}</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# --- Task List ---
if not tasks:
    st.balloons()
    st.success(f"🎉 お疲れ様でした！今日の優先課題はすべて完了です！")
else:
    rows = [tasks[i:i + 2] for i in range(0, len(tasks), 2)]
    for row in rows:
        cols = st.columns(2)
        for idx, task in enumerate(row):
            with cols[idx]:
                if task["lv2"]: stage_name, stage_color, progress_pct, target_check_col = "Lv3", "#3b82f6", "66%", WRITE_COL_LV3
                elif task["lv1"]: stage_name, stage_color, progress_pct, target_check_col = "Lv2", "#8b5cf6", "33%", WRITE_COL_LV2
                else: stage_name, stage_color, progress_pct, target_check_col = "Lv1", "#10b981", "5%", WRITE_COL_LV1
                
                border_color = "#ef4444" if task["score"] >= 100 else ("#f59e0b" if task["score"] >= 50 else "#10b981")

                st.markdown(f"""<div class="task-card"><div class="card-header-bar" style="background-color: {border_color};"></div><div class="card-content">""", unsafe_allow_html=True)
                c_img, c_info = st.columns([1, 1])
                with c_img:
                    if task["img"]: st.image(task["img"])
                    else: st.warning("No Image")
                with c_info:
                    st.markdown(f"""<div class="stage-badge" style="background-color: {stage_color};">{stage_name}</div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="info-label">LAST REVIEWED</div><div class="date-text">📅 {task['date'] if task['date'] else '🆕 初挑戦'}</div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="progress-track"><div class="progress-fill" style="width: {progress_pct}; background-color: {stage_color};"></div></div>""", unsafe_allow_html=True)
                    
                    if st.button("🟢 余裕", key=f"e_{task['index']}", use_container_width=True):
                        sheet.update_cell(task["index"], target_check_col, True)
                        sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                        st.toast(f"ナイス！出題間隔をあけます🚀", icon="🎉")
                        time.sleep(1); st.rerun()
                    if st.button("🟡 微妙", key=f"s_{task['index']}", use_container_width=True):
                        sheet.update_cell(task["index"], WRITE_COL_DATE, tomorrow_str if stage_name=="Lv1" else today_str)
                        st.toast("OK！忘れないうちにまた復習しましょう💪", icon="🔄")
                        time.sleep(1); st.rerun()
                    if st.button("🔴 敗北", key=f"b_{task['index']}", use_container_width=True):
                        sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                        if task["lv2"]: sheet.update_cell(task["index"], WRITE_COL_LV2, "FALSE")
                        elif task["lv1"]: sheet.update_cell(task["index"], WRITE_COL_LV1, "FALSE")
                        st.toast("ドンマイ！明日またリベンジしましょう🔥", icon="📉")
                        time.sleep(1); st.rerun()
                st.markdown('</div></div>', unsafe_allow_html=True)

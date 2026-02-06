import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import time

# ==========================================
# ⚙️ 設定エリア
# ==========================================
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
st.set_page_config(page_title="Weakness Tracker", page_icon="🎯", layout="wide")

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

    /* --- タイトルのデザイン調整 --- */
    h1 {
        font-family: 'Zen Maru Gothic', sans-serif;
        font-size: 36px !important;
        font-weight: 900 !important;
        letter-spacing: -2px !important;
        color: #0f172a !important;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }

    /* --- メトリクスエリア --- */
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

    /* --- カード本体 --- */
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

    /* --- 画像スタイル --- */
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
    
    /* ボタン間の余白調整 */
    .stButton button {
        margin-bottom: 4px;
    }

    /* --- トースト通知（st.toast）の完全修正版 --- */
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
        min-height: auto !important;
        display: flex !important;
        align-items: flex-start !important;
        overflow: visible !important;
    }
    
    div[data-testid="stToast"] [data-testid="stToastIcon"] {
        font-size: 12px !important;
        line-height: 1.2 !important;
        margin-right: 14px !important;
        flex-shrink: 0 !important;
    }

    div[data-testid="stToast"] [data-testid="stMarkdownContainer"] {
        flex-grow: 1 !important;
    }

    div[data-testid="stToast"] [data-testid="stMarkdownContainer"] p {
        font-size: 12px !important;
        font-weight: 700 !important;
        color: #1e293b !important;
        line-height: 1.5 !important; /* 行間を広めに確保 */
        margin: 0 !important;
        padding: 0 !important;
        white-space: normal !important;
    }

    /* --- スマホ調整 --- */
    @media only screen and (max-width: 600px) {
        div[data-testid="stImage"] img {
            max-height: 500px;
        }
        [data-testid="column"] {
            padding: 0 !important;
        }
        .metric-container {
            margin-bottom: 8px;
        }
    }
    
    /* --- Streamlit標準UI非表示 --- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
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
    if not isinstance(url, str): return None
    file_id = None
    if "drive.google.com" in url and "id=" in url:
        try: file_id = url.split('id=')[1].split('&')[0]
        except: pass
    elif "drive.google.com" in url and "/d/" in url:
        try: file_id = url.split('/d/')[1].split('/')[0]
        except: pass
    if file_id:
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    return url

# --- データ処理 ---
df = get_data()
tasks = []

stats = {
    "total_active": 0, 
    "graduated": 0,    
}

JST = timedelta(hours=9)
today_date = (datetime.utcnow() + JST).date()
today_str = (datetime.utcnow() + JST).strftime('%Y/%m/%d')

with st.sidebar:
    st.header("⚙️ 設定")
    min_score = st.slider("最低優先度", 0, 100, 70)

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

        if lv3:
            stats["graduated"] += 1
        else:
            stats["total_active"] += 1

        # 今日やったか判定
        is_today_done = False
        if last_date:
            try:
                if len(last_date.split('/')) == 3:
                    ld_obj = datetime.strptime(last_date, '%Y/%m/%d').date()
                elif len(last_date.split('/')) == 2:
                    ld_obj = datetime.strptime(last_date, '%m/%d').date().replace(year=today_date.year)
                else:
                    ld_obj = None
                
                if ld_obj == today_date:
                    is_today_done = True
            except: pass

        if not lv3 and score >= min_score and not is_today_done:
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
# メインUI構築
# ==========================================
st.markdown(f"""
    <h1 style='font-family: "Zen Maru Gothic", sans-serif; font-weight: 900; font-size: 36px; color: #0f172a; margin-bottom: 0;'>
        🎯 反復学習サポート
    </h1>
""", unsafe_allow_html=True)
st.caption("Strategic Learning Management System")

# ★追加：自己評価の基準ガイド
with st.expander("💡 評価のめやす（どのボタンを押す？）"):
    st.markdown("""
    - **🟢 余裕** ： 見た瞬間に解法が浮かび、迷わず解けた！ 
        - → <span style='color:#10b981; font-weight:bold;'>Lvが進み、次は数日〜1ヶ月後に出ます。</span>
    - **🟡 微妙** ： 解けたけど時間がかかった。少し自信がない。 
        - → <span style='color:#f59e0b; font-weight:bold;'>Lvは維持。忘れないうちに数日後に再出題されます。</span>
    - **🔴 敗北** ： 解き方がわからなかった。間違えてしまった。 
        - → <span style='color:#ef4444; font-weight:bold;'>Lvが下がるか、明日すぐリベンジ出題されます。</span>
    """, unsafe_allow_html=True)


# ダッシュボード
m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">🔥 今日の課題</div>
        <div class="metric-value">{len(tasks)}</div>
    </div>
    """, unsafe_allow_html=True)
high_priority_count = sum(1 for t in tasks if t["score"] >= 100)
with m2:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">🚨 最優先</div>
        <div class="metric-value danger">{high_priority_count}</div>
    </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">🎓 達成</div>
        <div class="metric-value success">{stats['graduated']}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

if not tasks:
    st.balloons()
    st.success("🎉 All priority tasks completed!")
    st.info(f"現在、未卒業の弱点は残り {stats['total_active']} 問です。サイドバーのフィルタを調整して復習しましょう！")
else:
    rows = [tasks[i:i + 2] for i in range(0, len(tasks), 2)]

    for row in rows:
        cols = st.columns(2)
        
        for idx, task in enumerate(row):
            with cols[idx]:
                if task["lv2"]:
                    stage_name = "Lv3"
                    stage_color = "#3b82f6"
                    progress_pct = "66%"
                    target_check_col = WRITE_COL_LV3
                elif task["lv1"]:
                    stage_name = "Lv2"
                    stage_color = "#8b5cf6"
                    progress_pct = "33%"
                    target_check_col = WRITE_COL_LV2
                else:
                    stage_name = "Lv1"
                    stage_color = "#10b981"
                    progress_pct = "5%"
                    target_check_col = WRITE_COL_LV1
                    
                if task["score"] >= 100: border_color = "#ef4444"
                elif task["score"] >= 50: border_color = "#f59e0b"
                else: border_color = "#10b981"

                st.markdown(f"""<div class="task-card">
                    <div class="card-header-bar" style="background-color: {border_color};"></div>
                    <div class="card-content">""", unsafe_allow_html=True)

                col_img, col_info = st.columns([1, 1])

                with col_img:
                    if task["img"]:
                        st.image(task["img"])
                    else:
                        st.warning("No Image")

                with col_info:
                    st.markdown(f"""
                    <div class="stage-badge" style="background-color: {stage_color};">
                        {stage_name}
                    </div>
                    """, unsafe_allow_html=True)

                    display_date = task["date"] if task["date"] else "🆕 初挑戦"
                    st.markdown(f"""
                    <div class="info-label" style="margin-top:0;">LAST REVIEWED</div>
                    <div class="date-text">📅 {display_date}</div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"""
                    <div class="progress-track">
                        <div class="progress-fill" style="width: {progress_pct}; background-color: {stage_color};"></div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ==========================================
                    # 👇 ボタンアクション (ヘルプ説明を追加)
                    # ==========================================
                    
                    # 🟢 余裕 (進級)
                    if st.button("🟢 余裕", key=f"easy_{task['index']}", use_container_width=True):
                        sheet.update_cell(task["index"], target_check_col, True)
                        sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                        st.toast(f"ナイス！次のレベル({stage_name}クリア)へ進みます🚀", icon="🎉")
                        time.sleep(1)
                        st.rerun()
                    
                    # 🟡 微妙 (維持)
                    if st.button("🟡 微妙", key=f"soso_{task['index']}", use_container_width=True):
                        if stage_name == "Lv1":
                            sheet.update_cell(task["index"], WRITE_COL_DATE, tomorrow_str)
                            msg = "OK！少し間隔をあけて（中1日）、もう一度練習しましょう💪"
                        else:
                            sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                            msg = "OK！Lvは維持します。忘れないうちにまた復習しましょう💪"
                        
                        st.toast(msg, icon="🔄")
                        time.sleep(1)
                        st.rerun()
                        
                    # 🔴 敗北 (降格)
                    if st.button("🔴 敗北", key=f"bad_{task['index']}", use_container_width=True):
                        sheet.update_cell(task["index"], WRITE_COL_DATE, today_str)
                        
                        demotion_msg = "ドンマイ！今は解けなかったので、また明日復習しましょう🔥"
                        
                        if task["lv2"]: 
                            sheet.update_cell(task["index"], WRITE_COL_LV2, "FALSE")
                            demotion_msg = "今は解けなかったので、Lv2に戻って基礎を固め直しましょう！🛡️"
                        elif task["lv1"]: 
                            sheet.update_cell(task["index"], WRITE_COL_LV1, "FALSE")
                            demotion_msg = "今は解けなかったので、Lv1に戻ってやり直しましょう！🌱"
                        
                        st.toast(demotion_msg, icon="📉")
                        time.sleep(1)
                        st.rerun()

                st.markdown('</div></div>', unsafe_allow_html=True)

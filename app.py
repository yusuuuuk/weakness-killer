import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date

# ==========================================
# ⚙️ 設定エリア（ここだけ確認してください！）
# ==========================================

# スプレッドシートの「列番号」の設定（A列=0, B列=1, C列=2...）
# ※「フォームの回答 1」シートの列順に合わせてください
COL_Q_NUM   = 3  # D列: 問題番号
COL_IMG_URL = 2  # C列: 画像URL（重要！ここがhttps~であること）
COL_LV1     = 5  # F列: 1回目 (Lv1)
COL_LV2     = 6  # G列: 2回目 (Lv2)
COL_LV3     = 7  # H列: 3回目 (Lv3)
COL_NEXT    = 8  # I列: スコア

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
    st.info("Secretsの worksheet_name が正しいか確認してください（推奨: 'フォームの回答 1'）")
    st.stop()

# --- 2. 関数定義 ---

def get_data():
    # 全データを取得
    all_values = sheet.get_all_values()
    # ヘッダー(1行目)とデータ(2行目以降)を分離
    if len(all_values) < 2:
        return pd.DataFrame()
    headers = all_values[0]
    df = pd.DataFrame(all_values[1:], columns=headers)
    return df

def convert_drive_url(url):
    # GoogleドライブのURLを表示可能な形式に変換
    if not isinstance(url, str):
        return None
    if "drive.google.com" in url and "id=" in url:
        # id=xxxxx の形式の場合
        try:
            file_id = url.split('id=')[1].split('&')[0]
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
        except:
            return url
    elif "drive.google.com" in url and "/d/" in url:
        # /d/xxxxx/view の形式の場合
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

today = date.today()
tasks = []

# 行ごとにデータを処理
for i, row in df.iterrows():
    try:
        # 列数チェック（エラー防止）
        if len(row) <= max(COL_Q_NUM, COL_IMG_URL, COL_NEXT):
            continue

        # データの取得
        q_num = row[COL_Q_NUM]
        raw_url = row[COL_IMG_URL]
        
        # URLが「http」で始まっているか確認
        if not str(raw_url).startswith("http"):
            # URLじゃない場合（文字の場合）はスキップ、またはプレースホルダー
            img_url = None
        else:
            img_url = convert_drive_url(raw_url)

        # チェックボックスの状態確認 ("TRUE" 文字列チェック)
        lv1 = str(row[COL_LV1]).upper() == "TRUE"
        lv2 = str(row[COL_LV2]).upper() == "TRUE"
        lv3 = str(row[COL_LV3]).upper() == "TRUE"
        
        # 次回日付の計算
        next_date_str = str(row[COL_NEXT])
        
        days_diff = -999 # 初期値
        
        if next_date_str and "卒業" not in next_date_str:
            try:
                # 日付形式の揺らぎに対応 (yyyy/mm/dd または mm/dd)
                if len(next_date_str.split('/')[0]) == 4:
                    next_date = datetime.strptime(next_date_str, "%Y/%m/%d").date()
                else:
                    # 年がない場合は今年とする
                    temp_date = datetime.strptime(next_date_str, "%m/%d").date()
                    next_date = temp_date.replace(year=today.year)
                
                days_diff = (today - next_date).days
            except:
                days_diff = 0 # 日付エラー時は今日やることにする

        # 表示条件: Lv3未完了 かつ 卒業じゃない かつ 期限が来ている
        is_graduated = lv3 or ("卒業" in next_date_str)
        if not is_graduated and days_diff >= 0:
            tasks.append({
                "index": i + 2, # スプレッドシートの行番号 (0始まり+ヘッダー分)
                "name": q_num,
                "img": img_url,
                "score": days_diff,
                "lv1": lv1, "lv2": lv2, "lv3": lv3
            })

    except Exception as e:
        # エラー行はスキップ
        continue

# 並び替え（スコアが高い＝滞納が長い順）
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
                    st.caption("※スプレッドシートのURL列を確認してください")
            
            with c2:
                # 危険度表示
                if task["score"] >= 3:
                    st.error(f"🚨 危険度: Lv{task['score']} (滞納中)")
                else:
                    st.info(f"🟢 本日の課題")
                
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
                    # スプレッドシートを更新
                    sheet.update_cell(task["index"], check_col, True)
                    st.toast(f"『{task['name']}』をクリアしました！")
                    import time
                    time.sleep(1)
                    st.rerun()

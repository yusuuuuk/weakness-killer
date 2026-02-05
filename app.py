import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# タイトル
st.title("🔥 Weakness Killer (算数)")

# --- 1. サイドバー（登録画面） ---
st.sidebar.header("新規問題登録")
uploaded_file = st.sidebar.file_uploader("問題の画像をアップ", type=['png', 'jpg'])
q_name = st.sidebar.text_input("問題番号 (例: 4(2))")

if st.sidebar.button("登録する"):
    if uploaded_file and q_name:
        # ここで画像を保存＆DB登録する処理を書く
        st.sidebar.success(f"『{q_name}』を登録しました！明日のクエストに追加されます。")
    else:
        st.sidebar.error("画像と番号は必須です")

# --- 2. メイン画面（今日の課題） ---
st.subheader("今日のクエスト")

# ダミーデータ（本来はDBから取得）
tasks = [
    {"name": "組分け 第9回 4(2)", "date": "2026-02-01", "score": 3, "img": "sample1.jpg"},
    {"name": "合不合 第1回 2(5)", "date": "2026-02-04", "score": 0, "img": "sample2.jpg"},
]

# リスト表示
for task in tasks:
    # カードのようなUIを作る
    with st.container():
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # 本当はアップされた画像を表示
            st.image("https://via.placeholder.com/300", caption="問題画像")
            
        with col2:
            # 危険度スコアで色を変える
            if task["score"] > 2:
                st.error(f"🚨 危険度: {task['score']} (放置中！)")
            else:
                st.info(f"🔰 危険度: {task['score']}")
            
            st.write(f"**{task['name']}**")
            st.write(f"登録日: {task['date']}")
            
            if st.button(f"クリア！ ({task['name']})"):
                st.balloons() # 風船が飛ぶ演出
                st.success("ナイス！次は1週間後に出題します。")

# --- 3. 分析グラフ ---
st.divider()
st.subheader("📊 現在の克服率")
st.progress(0.6) # プログレスバー
st.caption("目標まであと40%！")

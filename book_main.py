import pandas as pd
import streamlit as st
import plotly.express as px
import os
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import hashlib
from datetime import date
import psycopg2
import os

@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="aws-1-ap-southeast-2.pooler.supabase.com",
        database="postgres",
        user="postgres.ulqyrqyfwvaqetvbprxo",
        password="wF9ZWFA5trrs4gJq",
        port=6543
    )

conn = get_connection()
c = conn.cursor()

login_flag = False
sign_in_flag = False

#usernameが使われていたら、それは使えないようにしないとだね

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(username, password):
    try:
        c.execute('INSERT INTO users(username, password_hash) VALUES (%s, %s)', (username, password))
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        conn.rollback()
        return False

def login_user(username, password):
    c.execute('SELECT * FROM users WHERE username = %s AND password_hash = %s', (username, password))
    data = c.fetchall()
    return data

def update_sql(edit_df,read_book_ids,now_user_id,today):
    edit_read = edit_df.loc[edit_df['read'] == True, 'book_id'].to_list()
    for id in edit_read:
        if id not in read_book_ids:
            c.execute(
                'INSERT INTO user_books (user_id ,book_id ,read_flag ,read_date) VALUES (%s,%s,%s,%s)', (now_user_id,id,True,today))
    conn.commit()
    st.success('登録が完了しました')
    st.rerun()

def main():
        # 1. セッション状態の初期化 (ログイン状態を保存する変数を準備)
    if "is_login" not in st.session_state:
        st.session_state["is_login"] = False
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = ""

    # 2. ログイン後の画面を表示する条件分岐
    if st.session_state["is_login"]:
        user_name = st.session_state['user_name']
        st.title(f"ようこそ、{st.session_state['user_name']} さん！")
        st.write('シリーズ別の読書率を出すよ！')
        st.write('本サイトはwikipediaを参照しています。また個人による非公式サイトです。')
        st.write('各シリーズは基本的にシリーズの順番に則って、下に行くほど最新作になるように表示しています。')
        st.write('登録の反映には数分程度遅れが出る場合があります。')

        #ここから各ユーザーに合わせた表を作成
        c.execute('SELECT user_id FROM users WHERE username = %s',(user_name,))
        temp_result = c.fetchone()
        if temp_result is not None:
            now_user_id = temp_result[0]
        else:
            now_user_id = None
        today = date.today()

        book_list_pandas = pd.read_sql("SELECT * FROM books",conn)
        book_list_pandas['read'] = False

        c.execute('SELECT book_id, read_date FROM user_books WHERE user_id = %s',(now_user_id,))
        read_book_ids = [row[0] for row in c.fetchall()]
        book_list_pandas.loc[book_list_pandas['book_id'].isin(read_book_ids),'read'] = True
        #genresを作るぞ！！
        genres = book_list_pandas['genre'].unique()
        circle_color_map = {'読了':"#1e90ff",'未読':"gray"}
        #ここまで、各ユーザーに合わせた表を作成

        have_read = len(read_book_ids)
        all_books_number = len(book_list_pandas)
        ratio = have_read/all_books_number
        st.write(f'読んだ本は{have_read}冊 / {all_books_number}冊です。{ratio*100:.1f}%')
        st.progress(ratio)

        tab1,tab2,tab3,tab4,tab5 = st.tabs(['1冊登録!','まとめて登録!','シリーズ別進捗率!','ジャンル検索','これまでの履歴'])
        with tab1:
            search = st.chat_input('読んだ本のタイトルを入力してください(一部でも可)')
            if search:
                st.session_state.results = book_list_pandas[book_list_pandas['title'].str.contains(search, na = False)].copy()

            if 'results' in st.session_state:
                st.write('読んだ本のflagにチェックしてください')
                edit_df = st.data_editor(st.session_state.results, num_rows= 'fixed',key="my_editor_title")
                
                if st.button('この本を登録する'):
                    update_sql(edit_df,read_book_ids,now_user_id,today)

        with tab2:
            st.write('読んだ本のreadにチェックしてください')
            edit_df = st.data_editor(book_list_pandas, num_rows='fixed')

            if st.button('登録する！'):
                update_sql(edit_df,read_book_ids,now_user_id,today)

        with tab3:
            col_0,col_1 = st.columns(2)
            cols = [col_0,col_1]
            for n,gn in enumerate(genres):
                col_num = n % 2
                with cols[col_num]:
                    sub_gn = book_list_pandas[book_list_pandas['genre'] == gn]
                    read = sub_gn[sub_gn['read']==True]
                    yet = sub_gn[sub_gn['read']==False]
                    read_books = sub_gn['read'].sum()
                    all_books = len(sub_gn)
                    counts = sub_gn['read'].value_counts()
                    st.write(f'{gn}　シリーズ')
                    fig = px.pie(
                        values = [len(read),len(yet)],
                        names = ['読了','未読'],
                        hole = 0.4,
                        color = ['読了','未読'],
                        color_discrete_map = circle_color_map
                    )
                    st.write(f'読んだ冊数　:　{read_books}冊　/　{all_books}冊')
                    fig.update_traces(sort = False)
                    st.plotly_chart(fig,use_container_width=True,key=f"pie_{gn}")
                    with st.expander('読んだ本/読んでいない本を見る'):
                        col1,col2 = st.columns(2)
                        with col1:
                            st.dataframe(read[['title']],hide_index = True)
                        with col2:
                            st.dataframe(yet[['title']],hide_index = True)
                    st.divider()
                
        with tab4:
            genre_counts = book_list_pandas['genre'].value_counts()
            genre_df = genre_counts.reset_index()
            genre_df.columns = ['ジャンル名', '冊数'] 
            st.dataframe(genre_df, hide_index=True)

            search = st.text_input('読んだ本のジャンルを入力してください(一部でも可)')
            if search:
                st.session_state.results2 = book_list_pandas[book_list_pandas['genre'].str.contains(search, na = False)].copy()

            if 'results2' in st.session_state:
                st.write('読んだ本のflagにチェックしてください。複数選択も可能です')
                edited_df2 = st.data_editor(st.session_state.results2, num_rows= 'fixed',key="my_editor_genre")
                
                if st.button('この本を登録する!!'):
                    update_sql(edited_df2,read_book_ids,now_user_id,today)

        #読んだ日付の変更も機能として入るといいね
        with tab5:
            query = '''
            SELECT b.title, u.read_date
            FROM user_books u
            INNER JOIN books b ON u.book_id = b.book_id
            WHERE u.user_id = %s
            '''

            record_pd = pd.read_sql(query, conn,params = (now_user_id,))
            unique_date = record_pd['read_date'].unique()
            for each_date in unique_date:
                title_list = record_pd.loc[record_pd['read_date'] == each_date, 'title'].to_list()
                st.write(f'{each_date}に読了した本はこちら')
                st.dataframe(title_list)
  

        # ログアウトボタン
        if st.sidebar.button("ログアウト"):
            st.session_state["is_login"] = False
            st.rerun() # 画面を更新
            
    else:
        # ログイン前のメニュー
        menu = ["ホーム", "ログイン", "サインアップ"]
        choice = st.sidebar.selectbox("メニュー", menu)

        if choice == "ホーム":
            st.subheader("左上の>>から、ログインかサインアップを選択してください")

        elif choice == "ログイン":
            st.subheader("ログイン画面です")
            username = st.sidebar.text_input("ユーザー名")
            password = st.sidebar.text_input("パスワード", type='password')

            if st.sidebar.button("ログイン"): # checkboxよりbuttonの方が自然です
                result = login_user(username, make_hashes(password))
                if result:
                    # ログイン成功時に情報を保存
                    st.session_state["is_login"] = True
                    st.session_state["user_name"] = username
                    st.success(f"{username}さんでログインしました")
                    st.rerun() # 画面をログイン後画面に切り替える
                else:
                    st.warning("ユーザー名かパスワードが間違っています")

        elif choice == "サインアップ":
            st.subheader("新しいアカウントを作成します")
            new_user = st.text_input("ユーザー名")
            new_password = st.text_input("パスワード", type='password')

            if st.button("サインアップ"):
                results = add_user(new_user, make_hashes(new_password))
                if results:
                    st.success("アカウントの作成に成功しました")
                    st.info("ログイン画面からログインしてください")
                else:
                    st.write('このユーザー名はすでに使われています！他のユーザー名で登録してください')

if __name__ == '__main__':
    main()

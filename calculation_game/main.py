from flask import render_template, session, redirect, url_for, request, flash
from random import randint
from datetime import datetime, timedelta
import sqlite3
from  calculation_game import app

sqlite_path = "calculation_game/db/calculation_game.sqlite3"

data = []

def get_db_connection():
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    return connection


def q(num): #難易度に応じて、２つの数字を返す関数を作る。（教科書10章）

    if num == 1:
        num1 = randint(1, 9)
        num2 = randint(11, 99)

    if num == 2:
        num1 = randint(11, 99)
        num2 = randint(11, 99)

    if num == 3:
        num1 = randint(51, 99)
        num2 = randint(101, 999)

    return num1, num2


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/login', methods=["GET"])
def login():
    your_name = request.args.get('name', '')
    your_password = request.args.get('password', '')

    if your_name and your_password: #名前とパスワードが「空欄」でなければ、
        connection = get_db_connection()
        cursor = connection.cursor()
        user_name = cursor.execute('SELECT name, password FROM game_record WHERE name=?', (your_name,))
        # cursor.execute("INSERT INTO game_record values('Gmail', '１０月', 1, 1, 1, 0, 100)")
        user_row = user_name.fetchone() #ユーザーの情報を１つ取得

        session['username'] = your_name
        session['password'] = your_password

        if user_row: #過去にプレー履歴があり、
            if your_password != user_row['password']: #かつパスワードが間違っていれば
                flash('パスワードが間違っています',  'failed')
                return redirect(url_for('index')) #logout関数は最後に記述
            else: #間違っていなければ
                flash('ログインに成功しました', 'sucess')
                return render_template('level.html')

        else:#過去にプレー履歴がないなら
            flash(f'{ your_name }さんですね！はじめまして！', 'sucess')
            return render_template('level.html')

    else: #名前とパスワードが「空欄」であれば、
        flash('名前かパスワードが空欄です', 'failed')
        return redirect(url_for('index'))


@app.route('/game', methods=["POST", "GET"])
def game():
    global data
    word=""
    if request.method == "GET": #最初の一回だけ処理される
        session['level'] = int(request.args.get('level'))

        #パラメータを初期化
        wrong = 0
        right = 0
        quest = 1
        rate = 0
        name = session['username']

        elapsed_time = timedelta(seconds=0)
        limit_time = timedelta(seconds=30) #初期値は30秒
        start_time = datetime.now()

        num1, num2 = q(session['level']) #問題を出題（事前に作った関数を利用)

        data = [name, session['password'], session['level'] ,quest-1, right, wrong, rate,
                elapsed_time, limit_time, start_time, num1, num2]
                #data[7], data[8], data[9], data[10], data[11]


         #答え
        return render_template("question.html", num1=num1, num2=num2 ,quest=quest, word="")

    else:#２回目以降の処理
        while (data[7] < data[8]) and (data[5] < 3):

            ans = data[10] * data[11] #num1 * num2

            try:
                user_answer = request.form['user_answer']
                if user_answer == "q":
                    flash("qが押されたので終了しました", 'failed')
                    break
                # question = input(f"{num1}×{num}= "
                if int(user_answer) == ans:
                    data[4] += 1
                    judge = 'sucess'
                    flash("正解です", judge)

                else:
                    data[5] += 1
                    data[8] -= timedelta(seconds=3)
                    judge = 'failed'
                    flash("不正解です。制限時間が３秒減りました", judge)

            except Exception as error:
                data[8] -= timedelta(seconds=3)
                judge = 'failed'
                flash("エラーです。数字を入力してください。", judge)

            finally:
                data[3] += 1 # (quest - 1 ) += 1
                data[7] = datetime.now() - data[9] #経過時間を更新
                #経過時間 = 現在時刻 - 開始時刻

            if data[5] == 3:
                flash("\n3回間違えたので終了です", 'failed')

            elif data[8] > data[7]: #制限時間 > 経過時間
                rest_time = data[8] - data[7]
                flash(f"残り時間は、{int(rest_time.seconds)} 秒です", judge)

                data[10], data[11] = q(session['level']) #num1とnum2を更新
                return render_template('question.html', num1=data[10], num2=data[11],quest=data[3])

            else:
                flash('\n30秒経過したので終了です', 'failed')

        #whileを抜けたら、データベースに登録する
        data[6] = int(data[4] / (data[3]) * 100) #正答率の計算
        columns = ['name', 'level', 'quest', 'right', 'wrong', 'rate']
        # data = [name, session['password'], selected_level ,quest-1, right, wrong, rate]

        #データベースに結果を登録
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO game_record(name, password, level, quest, right, wrong, rate) VALUES(?,?,?,?,?,?,?)",
                        ( *data[:7] ,)          #(data[0], data[1], data[2], data[3], data[4], data[5], data[6])
                       )
        connection.commit()


        #結果発表のために、データ整理
        connection = get_db_connection()
        cursor = connection.cursor()
        players = cursor.execute("SELECT name, level, quest, right, wrong, rate FROM game_record WHERE level=? ORDER BY right DESC, rate DESC LIMIT 5", (session['level'],))
        rank = [1, 2, 3, 4, 5]
        return render_template('result.html', data=data[:7], top_players=zip(rank, players.fetchall()), columns=columns, word=word, level=session['level'])


@app.route('/again')
def again():
    flash('もう１度がんばりましょう')
    return render_template('level.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('ログアウトしました', 'failed')
    return redirect(url_for('index'))

@app.route('/delete')
def delete():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('DELETE FROM game_record WHERE name=?', (session['username'],))
    connection.commit()
    connection.close()
    flash('ユーザーデータを消去しました', 'failed')
    return redirect(url_for('index'))

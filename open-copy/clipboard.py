from flask import Flask, request, render_template, flash  
from flask_socketio import SocketIO, send
import sqlite3  
import os  
  
app = Flask(__name__)  
app.config['SECRET_KEY'] = 'secret!'  
socketio = SocketIO(app)  
  
DATABASE = 'clipboard.db'  
  
def get_db_connection():  
    conn = sqlite3.connect(DATABASE)  
    conn.row_factory = sqlite3.Row  
    return conn  
  
def init_db():  
    with get_db_connection() as conn:  
        cursor = conn.cursor()  
        cursor.execute('''  
            CREATE TABLE IF NOT EXISTS clipboard (  
                id INTEGER PRIMARY KEY AUTOINCREMENT,  
                content TEXT NOT NULL  
            )  
        ''')  
        cursor.execute('SELECT * FROM clipboard')  
        if not cursor.fetchone():  
            cursor.execute('''INSERT INTO clipboard (content) VALUES ('')''')  
        conn.commit()  
  
if not os.path.exists(DATABASE):  
    init_db()  
  
@app.route('/', methods=['GET', 'POST'])  
def clipboard():  
    if request.method == 'POST':  
        content = request.form['content']  
        try:  
            with get_db_connection() as conn:  
                cursor = conn.cursor()  
                cursor.execute('UPDATE clipboard SET content = ?', (content,))  
                conn.commit()  
                socketio.emit('content_updated', {'content': content})  
            flash('剪切板内容已更新', 'success')  
        except Exception as e:  
            flash(f'无法更新剪切板: {e}', 'error')  
  
    try:  
        with get_db_connection() as conn:  
            cursor = conn.cursor()  
            cursor.execute('SELECT content FROM clipboard')  
            content = cursor.fetchone()['content']  
    except Exception as e:  
        flash(f'无法读取剪切板: {e}', 'error')  
        content = ''  
  
    return render_template('clipboard.html', content=content)  
  
@socketio.on('connect')  
def handle_connect():  
    print('Client connected')  
    try:  
        with get_db_connection() as conn:  
            cursor = conn.cursor()  
            cursor.execute('SELECT content FROM clipboard')  
            content = cursor.fetchone()['content']  
            socketio.emit('content_updated', {'content': content})  
    except Exception as e:  
        print(f'Error sending initial content: {e}')  
  
@socketio.on('disconnect')  
def handle_disconnect():  
    print('Client disconnected')  
  
if __name__ == '__main__':  
    socketio.run(app, host='0.0.0.0', port=8000, allow_unsafe_werkzeug=True)

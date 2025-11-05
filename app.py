from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import bcrypt
from datetime import datetime
import sqlite3
import os
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app, supports_credentials=True)

# Настройки базы данных
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data.db')

def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица задач
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            completed BOOLEAN DEFAULT FALSE,
            priority TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    """Контекстный менеджер для подключения к БД"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Инициализируем БД при старте
init_database()

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' in session:
        with get_db_connection() as conn:
            user = conn.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            if user:
                return render_template('index.html', username=user['username'])
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect('/')
            else:
                return render_template('login.html', error='Неверное имя пользователя или пароль')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            return render_template('register.html', error='Пароли не совпадают')
        
        if len(password) < 6:
            return render_template('register.html', error='Пароль должен содержать не менее 6 символов')
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        try:
            with get_db_connection() as conn:
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
                conn.commit()
                
                user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
                session['user_id'] = user['id']
                session['username'] = username
                
            return redirect('/')
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Пользователь с таким именем уже существует')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect('/login')

# API маршруты
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    if 'user_id' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    with get_db_connection() as conn:
        tasks = conn.execute('''
            SELECT id, text, completed, priority, created_at 
            FROM tasks WHERE user_id = ? ORDER BY created_at DESC
        ''', (session['user_id'],)).fetchall()
        
        tasks_list = []
        for task in tasks:
            tasks_list.append({
                'id': task['id'],
                'text': task['text'],
                'completed': bool(task['completed']),
                'priority': task['priority'],
                'created_at': task['created_at']
            })
        
        return jsonify(tasks_list)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'Текст задачи обязателен'}), 400
    
    text = data['text']
    priority = data.get('priority', 'medium')
    
    with get_db_connection() as conn:
        cursor = conn.execute(
            'INSERT INTO tasks (user_id, text, priority) VALUES (?, ?, ?)',
            (session['user_id'], text, priority)
        )
        conn.commit()
        
        new_task = {
            'id': cursor.lastrowid,
            'text': text,
            'completed': False,
            'priority': priority,
            'created_at': datetime.now().isoformat()
        }
        
        return jsonify(new_task), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    data = request.get_json()
    
    with get_db_connection() as conn:
        # Проверяем, что задача принадлежит пользователю
        task = conn.execute(
            'SELECT * FROM tasks WHERE id = ? AND user_id = ?',
            (task_id, session['user_id'])
        ).fetchone()
        
        if not task:
            return jsonify({'error': 'Задача не найдена'}), 404
        
        # Обновляем поля
        update_fields = []
        params = []
        
        if 'text' in data:
            update_fields.append('text = ?')
            params.append(data['text'])
        
        if 'completed' in data:
            update_fields.append('completed = ?')
            params.append(1 if data['completed'] else 0)
        
        if 'priority' in data:
            update_fields.append('priority = ?')
            params.append(data['priority'])
        
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        
        if update_fields:
            params.extend([task_id, session['user_id']])
            conn.execute(
                f'UPDATE tasks SET {", ".join(update_fields)} WHERE id = ? AND user_id = ?',
                params
            )
            conn.commit()
        
        # Возвращаем обновленную задачу
        updated_task = conn.execute(
            'SELECT id, text, completed, priority, created_at FROM tasks WHERE id = ?',
            (task_id,)
        ).fetchone()
        
        return jsonify({
            'id': updated_task['id'],
            'text': updated_task['text'],
            'completed': bool(updated_task['completed']),
            'priority': updated_task['priority'],
            'created_at': updated_task['created_at']
        })

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    with get_db_connection() as conn:
        result = conn.execute(
            'DELETE FROM tasks WHERE id = ? AND user_id = ?',
            (task_id, session['user_id'])
        )
        conn.commit()
        
        if result.rowcount == 0:
            return jsonify({'error': 'Задача не найдена'}), 404
        
        return jsonify({'message': 'Задача удалена'})

@app.route('/api/tasks/clear-completed', methods=['DELETE'])
def clear_completed():
    if 'user_id' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    with get_db_connection() as conn:
        conn.execute(
            'DELETE FROM tasks WHERE user_id = ? AND completed = TRUE',
            (session['user_id'],)
        )
        conn.commit()
        
        return jsonify({'message': 'Выполненные задачи удалены'})

@app.route('/api/user')
def get_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    return jsonify({
        'username': session.get('username'),
        'user_id': session.get('user_id')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
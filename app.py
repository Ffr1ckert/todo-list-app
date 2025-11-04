from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import json
import os
import bcrypt
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Для Render нужно настроить CORS правильно
CORS(app, supports_credentials=True)

# На Render используем абсолютные пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, 'data', 'users.json')
TASKS_FILE = os.path.join(BASE_DIR, 'data', 'tasks.json')

def ensure_data_directory():
    """Создает папку data если её нет"""
    data_dir = os.path.join(BASE_DIR, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

def ensure_json_files():
    """Создает JSON файлы если они не существуют или повреждены"""
    ensure_data_directory()
    
    # Для users.json
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    else:
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    json.loads(content)
        except (json.JSONDecodeError, Exception):
            print("Восстановление users.json...")
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    # Для tasks.json
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    else:
        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    json.loads(content)
        except (json.JSONDecodeError, Exception):
            print("Восстановление tasks.json...")
            with open(TASKS_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

def load_users():
    """Загрузка пользователей из файла"""
    ensure_json_files()
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Ошибка загрузки users.json: {e}")
        return {}

def save_users(users):
    """Сохранение пользователей в файл"""
    try:
        ensure_data_directory()
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения users.json: {e}")

def load_tasks():
    """Загрузка задач из файла"""
    ensure_json_files()
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Ошибка загрузки tasks.json: {e}")
        return {}

def save_tasks(tasks):
    """Сохранение задач в файл"""
    try:
        ensure_data_directory()
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения tasks.json: {e}")

def get_user_tasks(username):
    """Получить задачи пользователя"""
    tasks = load_tasks()
    return tasks.get(username, [])

def save_user_tasks(username, user_tasks):
    """Сохранить задачи пользователя"""
    tasks = load_tasks()
    tasks[username] = user_tasks
    save_tasks(tasks)

@app.route('/')
def index():
    """Главная страница"""
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users = load_users()
        
        if username in users and bcrypt.checkpw(password.encode('utf-8'), users[username]['password'].encode('utf-8')):
            session['username'] = username
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
        
        users = load_users()
        
        if username in users:
            return render_template('register.html', error='Пользователь с таким именем уже существует')
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        users[username] = {
            'password': hashed_password,
            'created_at': datetime.now().isoformat()
        }
        save_users(users)
        
        tasks = load_tasks()
        tasks[username] = []
        save_tasks(tasks)
        
        session['username'] = username
        return redirect('/')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.pop('username', None)
    return redirect('/login')

# API маршруты
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    if 'username' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    tasks = get_user_tasks(session['username'])
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    if 'username' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'Текст задачи обязателен'}), 400
    
    tasks = get_user_tasks(session['username'])
    
    task_id = max([task['id'] for task in tasks], default=0) + 1
    
    new_task = {
        'id': task_id,
        'text': data['text'],
        'completed': False,
        'created_at': datetime.now().isoformat(),
        'priority': data.get('priority', 'medium')
    }
    
    tasks.append(new_task)
    save_user_tasks(session['username'], tasks)
    
    return jsonify(new_task), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    if 'username' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    data = request.get_json()
    tasks = get_user_tasks(session['username'])
    
    for task in tasks:
        if task['id'] == task_id:
            if 'text' in data:
                task['text'] = data['text']
            if 'completed' in data:
                task['completed'] = data['completed']
            if 'priority' in data:
                task['priority'] = data['priority']
            
            task['updated_at'] = datetime.now().isoformat()
            save_user_tasks(session['username'], tasks)
            return jsonify(task)
    
    return jsonify({'error': 'Задача не найдена'}), 404

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'username' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    tasks = get_user_tasks(session['username'])
    
    for i, task in enumerate(tasks):
        if task['id'] == task_id:
            deleted_task = tasks.pop(i)
            save_user_tasks(session['username'], tasks)
            return jsonify(deleted_task)
    
    return jsonify({'error': 'Задача не найдена'}), 404

@app.route('/api/tasks/clear-completed', methods=['DELETE'])
def clear_completed():
    if 'username' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    tasks = get_user_tasks(session['username'])
    remaining_tasks = [task for task in tasks if not task['completed']]
    save_user_tasks(session['username'], remaining_tasks)
    return jsonify({'message': 'Выполненные задачи удалены', 'count': len(remaining_tasks)})

@app.route('/api/user')
def get_user():
    if 'username' not in session:
        return jsonify({'error': 'Требуется аутентификация'}), 401
    
    users = load_users()
    user_data = users.get(session['username'], {})
    
    return jsonify({
        'username': session['username'],
        'created_at': user_data.get('created_at', '')
    })

# Гарантируем, что JSON файлы существуют при старте
ensure_json_files()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
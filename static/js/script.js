class TodoApp {
    constructor() {
        this.tasks = [];
        this.currentFilter = 'all';
        this.editingTaskId = null;
        this.apiBaseUrl = '/api';
        
        this.initElements();
        this.initEventListeners();
        this.loadTasks();
        this.updateDate();
    }

    initElements() {
        this.taskInput = document.getElementById('taskInput');
        this.prioritySelect = document.getElementById('prioritySelect');
        this.addBtn = document.getElementById('addBtn');
        this.tasksList = document.getElementById('tasksList');
        this.emptyState = document.getElementById('emptyState');
        this.totalTasks = document.getElementById('totalTasks');
        this.completedTasks = document.getElementById('completedTasks');
        this.pendingTasks = document.getElementById('pendingTasks');
        this.currentDate = document.getElementById('currentDate');
        this.filterBtns = document.querySelectorAll('.filter-btn');
        this.clearCompletedBtn = document.getElementById('clearCompletedBtn');
        
        // Модальное окно
        this.modal = document.getElementById('editModal');
        this.editTaskInput = document.getElementById('editTaskInput');
        this.editPrioritySelect = document.getElementById('editPrioritySelect');
        this.saveEditBtn = document.getElementById('saveEditBtn');
        this.cancelEditBtn = document.getElementById('cancelEditBtn');
        this.closeModal = document.querySelector('.close');
    }

    initEventListeners() {
        this.addBtn.addEventListener('click', () => this.addTask());
        this.taskInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addTask();
        });

        this.filterBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.filterBtns.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentFilter = e.target.dataset.filter;
                this.renderTasks();
            });
        });

        this.clearCompletedBtn.addEventListener('click', () => this.clearCompletedTasks());
        
        // Модальное окно
        this.saveEditBtn.addEventListener('click', () => this.saveEdit());
        this.cancelEditBtn.addEventListener('click', () => this.closeEditModal());
        this.closeModal.addEventListener('click', () => this.closeEditModal());
        
        window.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeEditModal();
            }
        });
    }

    async loadTasks() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/tasks`);
            if (response.ok) {
                this.tasks = await response.json();
                this.renderTasks();
            } else if (response.status === 401) {
                // Не авторизован - перенаправляем на страницу входа
                window.location.href = '/login';
            } else {
                this.showNotification('Ошибка загрузки задач', 'error');
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
            this.showNotification('Ошибка загрузки задач', 'error');
        }
    }

    async addTask() {
        const text = this.taskInput.value.trim();
        if (text === '') {
            this.showNotification('Введите текст задачи!', 'warning');
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/tasks`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: text,
                    priority: this.prioritySelect.value
                })
            });

            if (response.ok) {
                const newTask = await response.json();
                this.tasks.push(newTask);
                this.renderTasks();
                this.taskInput.value = '';
                this.taskInput.focus();
                this.showNotification('Задача успешно добавлена!', 'success');
            } else if (response.status === 401) {
                window.location.href = '/login';
            } else {
                this.showNotification('Ошибка добавления задачи', 'error');
            }
        } catch (error) {
            console.error('Error adding task:', error);
            this.showNotification('Ошибка добавления задачи', 'error');
        }
    }

    async toggleTask(id) {
        try {
            const task = this.tasks.find(t => t.id === id);
            const response = await fetch(`${this.apiBaseUrl}/tasks/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    completed: !task.completed
                })
            });

            if (response.ok) {
                const updatedTask = await response.json();
                const index = this.tasks.findIndex(t => t.id === id);
                this.tasks[index] = updatedTask;
                this.renderTasks();
                
                if (updatedTask.completed) {
                    this.showNotification('Задача отмечена как выполненная!', 'success');
                }
            } else if (response.status === 401) {
                window.location.href = '/login';
            } else {
                this.showNotification('Ошибка обновления задачи', 'error');
            }
        } catch (error) {
            console.error('Error toggling task:', error);
            this.showNotification('Ошибка обновления задачи', 'error');
        }
    }

    openEditModal(id) {
        const task = this.tasks.find(t => t.id === id);
        if (task) {
            this.editingTaskId = id;
            this.editTaskInput.value = task.text;
            this.editPrioritySelect.value = task.priority;
            this.modal.style.display = 'block';
        }
    }

    closeEditModal() {
        this.modal.style.display = 'none';
        this.editingTaskId = null;
    }

    async saveEdit() {
        const text = this.editTaskInput.value.trim();
        if (text === '') {
            this.showNotification('Текст задачи не может быть пустым!', 'warning');
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/tasks/${this.editingTaskId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: text,
                    priority: this.editPrioritySelect.value
                })
            });

            if (response.ok) {
                const updatedTask = await response.json();
                const index = this.tasks.findIndex(t => t.id === this.editingTaskId);
                this.tasks[index] = updatedTask;
                this.renderTasks();
                this.closeEditModal();
                this.showNotification('Задача обновлена!', 'success');
            } else if (response.status === 401) {
                window.location.href = '/login';
            } else {
                this.showNotification('Ошибка обновления задачи', 'error');
            }
        } catch (error) {
            console.error('Error updating task:', error);
            this.showNotification('Ошибка обновления задачи', 'error');
        }
    }

    async deleteTask(id) {
        if (confirm('Вы уверены, что хотите удалить эту задачу?')) {
            try {
                const response = await fetch(`${this.apiBaseUrl}/tasks/${id}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    this.tasks = this.tasks.filter(task => task.id !== id);
                    this.renderTasks();
                    this.showNotification('Задача удалена!', 'info');
                } else if (response.status === 401) {
                    window.location.href = '/login';
                } else {
                    this.showNotification('Ошибка удаления задачи', 'error');
                }
            } catch (error) {
                console.error('Error deleting task:', error);
                this.showNotification('Ошибка удаления задачи', 'error');
            }
        }
    }

    async clearCompletedTasks() {
        if (confirm('Вы уверены, что хотите удалить все выполненные задачи?')) {
            try {
                const response = await fetch(`${this.apiBaseUrl}/tasks/clear-completed`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    const result = await response.json();
                    this.tasks = this.tasks.filter(task => !task.completed);
                    this.renderTasks();
                    this.showNotification(`Удалено выполненных задач: ${result.count}`, 'info');
                } else if (response.status === 401) {
                    window.location.href = '/login';
                } else {
                    this.showNotification('Ошибка очистки задач', 'error');
                }
            } catch (error) {
                console.error('Error clearing completed tasks:', error);
                this.showNotification('Ошибка очистки задач', 'error');
            }
        }
    }

    renderTasks() {
        this.tasksList.innerHTML = '';
        
        let filteredTasks = this.tasks;
        
        if (this.currentFilter === 'active') {
            filteredTasks = this.tasks.filter(task => !task.completed);
        } else if (this.currentFilter === 'completed') {
            filteredTasks = this.tasks.filter(task => task.completed);
        }
        
        filteredTasks.forEach(task => {
            const taskElement = document.createElement('div');
            taskElement.className = `task-item ${task.completed ? 'completed' : ''} priority-${task.priority}`;
            taskElement.innerHTML = `
                <input type="checkbox" class="task-checkbox" ${task.completed ? 'checked' : ''}>
                <span class="task-text ${task.completed ? 'completed' : ''}">${this.escapeHtml(task.text)}</span>
                <span class="task-priority">${this.getPriorityText(task.priority)}</span>
                <div class="task-actions">
                    <button class="action-btn edit-btn" title="Редактировать">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn delete-btn" title="Удалить">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;

            const checkbox = taskElement.querySelector('.task-checkbox');
            const editBtn = taskElement.querySelector('.edit-btn');
            const deleteBtn = taskElement.querySelector('.delete-btn');

            checkbox.addEventListener('change', () => this.toggleTask(task.id));
            editBtn.addEventListener('click', () => this.openEditModal(task.id));
            deleteBtn.addEventListener('click', () => this.deleteTask(task.id));

            this.tasksList.appendChild(taskElement);
        });

        this.updateEmptyState();
        this.updateStats();
    }

    updateEmptyState() {
        if (this.tasks.length === 0) {
            this.emptyState.classList.remove('hidden');
        } else {
            this.emptyState.classList.add('hidden');
        }
    }

    updateStats() {
        const total = this.tasks.length;
        const completed = this.tasks.filter(task => task.completed).length;
        const pending = total - completed;
        
        this.totalTasks.textContent = `Всего задач: ${total}`;
        this.completedTasks.textContent = `Выполнено: ${completed}`;
        this.pendingTasks.textContent = `Осталось: ${pending}`;
    }

    updateDate() {
        const now = new Date();
        const options = { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        };
        this.currentDate.textContent = now.toLocaleDateString('ru-RU', options);
    }

    getPriorityText(priority) {
        switch(priority) {
            case 'low': return 'Низкий';
            case 'medium': return 'Средний';
            case 'high': return 'Высокий';
            default: return 'Средний';
        }
    }

    showNotification(message, type) {
        // Создаем элемент уведомления
        const notification = document.createElement('div');
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'success' ? '#4CAF50' : type === 'warning' ? '#FF9800' : type === 'error' ? '#F44336' : '#2196F3'};
            color: white;
            border-radius: 5px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
            max-width: 300px;
        `;
        
        document.body.appendChild(notification);
        
        // Удаляем уведомление через 3 секунды
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Добавляем стили для анимации уведомлений
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    new TodoApp();
});
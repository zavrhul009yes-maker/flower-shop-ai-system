from flask import Flask, render_template, jsonify, request, send_file, session
from flask_cors import CORS
import threading
import time
import json
import os
from datetime import datetime

from config import Config
from src.flower_shop import RealTimeFlowerShop
from src.dashboard import RealTimeDashboard
from src.database import init_db, get_db_stats, export_database_csv

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Инициализация базы данных
init_db(app)

# Глобальные переменные
shop = None
dashboard = None
simulation_thread = None
is_running = False

@app.before_first_request
def initialize():
    """Инициализация при первом запросе"""
    global shop, dashboard
    if shop is None:
        shop = RealTimeFlowerShop(
            initial_budget=app.config['INITIAL_BUDGET'],
            daily_customers=app.config['DAILY_CUSTOMERS']
        )
        dashboard = RealTimeDashboard(shop)
    print("✅ Система инициализирована")

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard_page():
    """Страница dashboard"""
    return render_template('dashboard.html')

@app.route('/database')
def database_page():
    """Страница управления базой данных"""
    return render_template('database.html')

# API endpoints
@app.route('/api/start', methods=['POST'])
def start_simulation():
    """Запуск симуляции"""
    global is_running, simulation_thread
    
    if not is_running:
        is_running = True
        
        def run_simulation():
            while is_running:
                shop.run_simulation_step()
                time.sleep(1)  # 1 секунда = 1 час в симуляции
        
        simulation_thread = threading.Thread(target=run_simulation, daemon=True)
        simulation_thread.start()
        
        return jsonify({'status': 'started', 'message': 'Симуляция запущена'})
    
    return jsonify({'status': 'already_running', 'message': 'Симуляция уже запущена'})

@app.route('/api/stop', methods=['POST'])
def stop_simulation():
    """Остановка симуляции"""
    global is_running
    
    if is_running:
        is_running = False
        return jsonify({'status': 'stopped', 'message': 'Симуляция остановлена'})
    
    return jsonify({'status': 'not_running', 'message': 'Симуляция не запущена'})

@app.route('/api/reset', methods=['POST'])
def reset_simulation():
    """Сброс симуляции"""
    global shop, dashboard, is_running
    
    is_running = False
    time.sleep(1)  # Даем время остановиться
    
    shop = RealTimeFlowerShop(
        initial_budget=app.config['INITIAL_BUDGET'],
        daily_customers=app.config['DAILY_CUSTOMERS']
    )
    dashboard = RealTimeDashboard(shop)
    
    return jsonify({'status': 'reset', 'message': 'Симуляция сброшена'})

@app.route('/api/status')
def get_status():
    """Получение текущего статуса"""
    if shop is None:
        return jsonify({'status': 'not_initialized'})
    
    data = shop.get_dashboard_data()
    return jsonify({
        'status': 'running' if is_running else 'stopped',
        'data': data
    })

@app.route('/api/recommendations/apply', methods=['POST'])
def apply_recommendations():
    """Применение рекомендаций ML"""
    if shop:
        shop.generate_recommendations()
        shop.apply_recommendations()
        return jsonify({'status': 'applied', 'message': 'Рекомендации применены'})
    return jsonify({'status': 'error', 'message': 'Магазин не инициализирован'})

@app.route('/api/database/stats')
def get_database_stats():
    """Получение статистики БД"""
    stats = get_db_stats()
    return jsonify(stats)

@app.route('/api/database/export')
def export_database():
    """Экспорт базы данных"""
    try:
        filename = export_database_csv()
        return send_file(
            filename,
            as_attachment=True,
            download_name=f'flower_shop_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/database/clear', methods=['POST'])
def clear_database():
    """Очистка базы данных"""
    try:
        from src.database import clear_database
        clear_database()
        return jsonify({'status': 'cleared', 'message': 'База данных очищена'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
import os
from datetime import timedelta

class Config:
    # Основные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # База данных
    SQLALCHEMY_DATABASE_URI = 'sqlite:///flower_shop.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки магазина
    INITIAL_BUDGET = 1000000
    DAILY_CUSTOMERS = 5000
    OPENING_TIME = 8
    CLOSING_TIME = 20
    
    # ML настройки
    ML_UPDATE_INTERVAL = 30  # секунды
    MODEL_SAVE_PATH = 'models/'
    
    # Настройки сессии
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Пути
    UPLOAD_FOLDER = 'uploads/'
    EXPORT_FOLDER = 'exports/'
    
    @staticmethod
    def init_app(app):
        # Создаем необходимые директории
        for folder in ['models', 'uploads', 'exports']:
            os.makedirs(folder, exist_ok=True)
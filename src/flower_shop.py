import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
from sklearn.ensemble import RandomForestRegressor
import sqlite3
import os

class RealTimeFlowerShop:
    def __init__(self, initial_budget=1000000, daily_customers=5000):
        self.budget = initial_budget
        self.daily_customers = daily_customers
        
        # Цветы и характеристики
        self.flowers = {
            'Розы': {'base_price': 150, 'cost': 80, 'popularity': 0.3},
            'Тюльпаны': {'base_price': 80, 'cost': 40, 'popularity': 0.2},
            'Хризантемы': {'base_price': 70, 'cost': 35, 'popularity': 0.15},
            'Герберы': {'base_price': 90, 'cost': 45, 'popularity': 0.12},
        }
        
        self.inventory = {flower: 1000 for flower in self.flowers}
        self.current_time = datetime.now()
        self.today_sales = {flower: 0 for flower in self.flowers}
        self.today_profit = {flower: 0.0 for flower in self.flowers}
        self.today_revenue = 0.0
        
        # ML модель
        self.demand_model = None
        self.current_recommendations = {
            'optimal_prices': {},
            'purchase_suggestions': {},
            'high_demand_flowers': []
        }
        
        # База данных
        self.db_path = 'flower_shop.db'
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Таблица продаж
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                flower TEXT,
                quantity INTEGER,
                price REAL,
                profit REAL
            )
        ''')
        
        # Таблица запасов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                flower TEXT,
                quantity INTEGER,
                price REAL
            )
        ''')
        
        self.conn.commit()
    
    def run_simulation_step(self):
        """Один шаг симуляции"""
        self.current_time += timedelta(hours=1)
        
        # Генерация спроса
        hour = self.current_time.hour
        if 8 <= hour < 20:  # Магазин открыт
            hourly_demand = self.generate_daily_demand()
            
            # Продажи по цветам
            for flower, stats in self.flowers.items():
                if self.inventory[flower] <= 0:
                    continue
                
                demand_share = stats['popularity'] * random.uniform(0.8, 1.2)
                flower_demand = int(hourly_demand * demand_share)
                possible_sales = min(flower_demand, self.inventory[flower])
                
                if possible_sales > 0:
                    current_price = self.get_current_price(flower)
                    cost = stats['cost']
                    
                    revenue = current_price * possible_sales
                    profit = (current_price - cost) * possible_sales
                    
                    self.inventory[flower] -= possible_sales
                    self.today_sales[flower] += possible_sales
                    self.today_profit[flower] += profit
                    self.today_revenue += revenue
                    self.budget += profit
                    
                    # Сохраняем в БД
                    self.save_sale(flower, possible_sales, current_price, profit)
        
        # Каждые 4 часа обновляем рекомендации
        if self.current_time.hour % 4 == 0:
            self.generate_recommendations()
            self.apply_recommendations()
        
        # Сохраняем запасы
        self.save_inventory()
        
        return sum(self.today_sales.values()), sum(self.today_profit.values())
    
    def generate_daily_demand(self):
        """Генерация спроса"""
        hour = self.current_time.hour
        hour_multipliers = {8: 0.3, 12: 0.8, 18: 1.0, 20: 0.5}
        hour_mult = hour_multipliers.get(hour, 0.5)
        
        weekday = self.current_time.weekday()
        weekday_mult = 1.3 if weekday >= 5 else 1.0
        
        return int(self.daily_customers * hour_mult * weekday_mult * random.uniform(0.9, 1.1))
    
    def get_current_price(self, flower):
        """Получение текущей цены"""
        base_price = self.flowers[flower]['base_price']
        
        if flower in self.current_recommendations['optimal_prices']:
            optimal_price = self.current_recommendations['optimal_prices'][flower]
            return optimal_price
        
        hour = self.current_time.hour
        if 18 <= hour <= 19:
            return base_price * 1.2
        return base_price
    
    def generate_recommendations(self):
        """Генерация ML рекомендаций"""
        # Оптимизация цен
        for flower in self.flowers:
            cost = self.flowers[flower]['cost']
            current_price = self.get_current_price(flower)
            
            # Простая оптимизация
            optimal_price = cost * 2.0  # 100% наценка
            optimal_price = max(optimal_price, cost * 1.3)
            optimal_price = min(optimal_price, cost * 3.0)
            optimal_price = round(optimal_price / 10) * 10
            
            self.current_recommendations['optimal_prices'][flower] = optimal_price
        
        # Рекомендации по закупкам
        for flower in self.flowers:
            current_inventory = self.inventory[flower]
            avg_sales = self.today_sales[flower] if self.current_time.hour > 8 else 10
            
            days_of_supply = current_inventory / avg_sales if avg_sales > 0 else 30
            
            if days_of_supply < 2:
                suggestion = 'СРОЧНО ЗАКУПИТЬ'
                quantity = int(avg_sales * 7)
            elif days_of_supply < 5:
                suggestion = 'ЗАКУПИТЬ'
                quantity = int(avg_sales * 5)
            else:
                suggestion = 'НОРМА'
                quantity = 0
            
            self.current_recommendations['purchase_suggestions'][flower] = {
                'suggestion': suggestion,
                'quantity': quantity,
                'days_of_supply': round(days_of_supply, 1)
            }
    
    def apply_recommendations(self):
        """Применение рекомендаций"""
        for flower, optimal_price in self.current_recommendations['optimal_prices'].items():
            self.flowers[flower]['base_price'] = optimal_price
        
        for flower, suggestion in self.current_recommendations['purchase_suggestions'].items():
            if suggestion['suggestion'] in ['СРОЧНО ЗАКУПИТЬ', 'ЗАКУПИТЬ']:
                quantity = suggestion['quantity']
                cost = self.flowers[flower]['cost'] * quantity
                
                if self.budget >= cost and quantity > 0:
                    self.inventory[flower] += quantity
                    self.budget -= cost
    
    def save_sale(self, flower, quantity, price, profit):
        """Сохранение продажи в БД"""
        self.cursor.execute('''
            INSERT INTO sales (timestamp, flower, quantity, price, profit)
            VALUES (?, ?, ?, ?, ?)
        ''', (self.current_time, flower, quantity, price, profit))
        self.conn.commit()
    
    def save_inventory(self):
        """Сохранение запасов в БД"""
        for flower, quantity in self.inventory.items():
            self.cursor.execute('''
                INSERT INTO inventory (timestamp, flower, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (self.current_time, flower, quantity, self.get_current_price(flower)))
        self.conn.commit()
    
    def get_dashboard_data(self):
        """Получение данных для dashboard"""
        return {
            'current_time': self.current_time.strftime('%Y-%m-%d %H:%M'),
            'budget': self.budget,
            'today_revenue': self.today_revenue,
            'today_profit': sum(self.today_profit.values()),
            'today_sales': sum(self.today_sales.values()),
            'inventory': [
                {
                    'flower': flower,
                    'quantity': quantity,
                    'price': self.get_current_price(flower),
                    'profit_today': self.today_profit[flower],
                    'sales_today': self.today_sales[flower]
                }
                for flower, quantity in self.inventory.items()
            ],
            'recommendations': self.current_recommendations
        }
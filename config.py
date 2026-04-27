import os


class Config:
    # Секретный ключ для безопасности (измените на свой!)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-change-me-12345'

    # База данных SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///dota_skill.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Папка для загрузки файлов
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB максимум

    # API OpenDota
    OPENDOTA_API_BASE = 'https://api.opendota.com/api'
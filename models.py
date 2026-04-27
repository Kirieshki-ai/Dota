from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    steam_id = db.Column(db.String(20), unique=True)
    avatar = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    player_stats = db.relationship('PlayerStats', backref='user', lazy=True, uselist=False)
    matches = db.relationship('MatchHistory', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class PlayerStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mmr_estimate = db.Column(db.Integer)
    winrate = db.Column(db.Float)
    total_games = db.Column(db.Integer)
    favorite_heroes = db.Column(db.Text)
    rank_tier = db.Column(db.Integer)
    leaderboard_rank = db.Column(db.Integer)
    performance_score = db.Column(db.Integer, default=0)
    extra_data = db.Column(db.Text)  # JSON с дополнительными данными
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def get_favorite_heroes(self):
        return json.loads(self.favorite_heroes) if self.favorite_heroes else []

    def get_extra_data(self):
        return json.loads(self.extra_data) if self.extra_data else {}


class MatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    match_id = db.Column(db.String(20), unique=True)
    hero_id = db.Column(db.Integer)
    hero_name = db.Column(db.String(100))  # Название героя
    kills = db.Column(db.Integer)
    deaths = db.Column(db.Integer)
    assists = db.Column(db.Integer)
    win = db.Column(db.Boolean)
    game_mode = db.Column(db.Integer)
    duration = db.Column(db.Integer)
    match_date = db.Column(db.DateTime)
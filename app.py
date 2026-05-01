from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, PlayerStats, MatchHistory, Replay
from forms import LoginForm, RegistrationForm, ProfileForm
from werkzeug.utils import secure_filename
import requests
import os
import json
import re
import csv
from io import StringIO
from datetime import datetime

# Создание приложения
app = Flask(__name__)
app.config.from_object(Config)

# Дополнительные настройки
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'

# ============================================
# ДАННЫЕ И СЛОВАРИ
# ============================================

RANK_NAMES = {
    1: "Herald", 2: "Guardian", 3: "Crusader",
    4: "Archon", 5: "Legend", 6: "Ancient",
    7: "Divine", 8: "Immortal"
}

HERO_NAMES = {}


def load_hero_names():
    """Загружает названия героев из OpenDota API"""
    global HERO_NAMES
    try:
        response = requests.get("https://api.opendota.com/api/heroes", timeout=5)
        if response.status_code == 200:
            for hero in response.json():
                HERO_NAMES[hero['id']] = hero['localized_name']
            print(f"✅ Загружено {len(HERO_NAMES)} героев из API")
            return True
    except Exception as e:
        print(f"⚠️ Ошибка загрузки героев: {e}")

    # Базовый список героев
    HERO_NAMES = {
        1: "Anti-Mage", 2: "Axe", 3: "Bane", 4: "Bloodseeker",
        5: "Crystal Maiden", 6: "Drow Ranger", 7: "Earthshaker",
        8: "Juggernaut", 9: "Mirana", 10: "Morphling",
        11: "Shadow Fiend", 12: "Phantom Lancer", 13: "Puck",
        14: "Pudge", 15: "Razor", 16: "Sand King", 17: "Storm Spirit",
        18: "Sven", 19: "Tiny", 20: "Vengeful Spirit",
        21: "Windranger", 22: "Zeus", 23: "Kunkka",
        25: "Lina", 26: "Lion", 27: "Shadow Shaman",
        28: "Slardar", 29: "Tidehunter", 30: "Witch Doctor",
        31: "Lich", 32: "Riki", 33: "Enigma",
        34: "Tinker", 35: "Sniper", 36: "Necrophos",
        37: "Warlock", 38: "Beastmaster", 39: "Queen of Pain",
        40: "Venomancer", 41: "Faceless Void", 42: "Wraith King",
        43: "Death Prophet", 44: "Phantom Assassin", 45: "Pugna",
        46: "Templar Assassin", 47: "Viper", 48: "Luna",
        49: "Dragon Knight", 50: "Dazzle", 51: "Clockwerk",
        52: "Leshrac", 53: "Nature's Prophet", 54: "Lifestealer",
        55: "Dark Seer", 56: "Clinkz", 57: "Omniknight",
        58: "Enchantress", 59: "Huskar", 60: "Night Stalker",
        61: "Broodmother", 62: "Bounty Hunter", 63: "Weaver",
        64: "Jakiro", 65: "Batrider", 66: "Chen",
        67: "Spectre", 68: "Ancient Apparition", 69: "Doom",
        70: "Ursa", 71: "Spirit Breaker", 72: "Gyrocopter",
        73: "Alchemist", 74: "Invoker", 75: "Silencer",
        76: "Outworld Destroyer", 77: "Lycan", 78: "Brewmaster",
        79: "Shadow Demon", 80: "Lone Druid", 81: "Chaos Knight",
        82: "Meepo", 83: "Treant Protector", 84: "Ogre Magi",
        85: "Undying", 86: "Rubick", 87: "Disruptor",
        88: "Nyx Assassin", 89: "Naga Siren", 90: "Keeper of the Light",
        91: "Io", 92: "Visage", 93: "Slark",
        94: "Medusa", 95: "Troll Warlord", 96: "Centaur Warrunner",
        97: "Magnus", 98: "Timbersaw", 99: "Bristleback",
        100: "Tusk", 101: "Skywrath Mage", 102: "Abaddon",
        103: "Elder Titan", 104: "Legion Commander", 105: "Techies",
        106: "Ember Spirit", 107: "Earth Spirit", 108: "Underlord",
        109: "Terrorblade", 110: "Phoenix", 111: "Oracle",
        112: "Winter Wyvern", 113: "Arc Warden", 114: "Monkey King",
        119: "Dark Willow", 120: "Pangolier", 121: "Grimstroke",
        123: "Hoodwink", 126: "Void Spirit", 128: "Snapfire",
        129: "Mars", 135: "Dawnbreaker", 136: "Marci",
        137: "Primal Beast", 138: "Muerta"
    }
    print(f"⚠️ Загружено {len(HERO_NAMES)} героев из локальной базы")
    return False


def get_rank_name(rank_tier):
    """Получает название ранга и количество звезд"""
    if not rank_tier or rank_tier == 0:
        return "Некалиброванный"

    medal_num = rank_tier // 10
    star_num = rank_tier % 10

    if medal_num in RANK_NAMES:
        rank_name = RANK_NAMES[medal_num]
        if rank_name == "Immortal":
            return "Immortal"
        stars = "⭐" * star_num if star_num > 0 else ""
        return f"{rank_name} {stars} [{star_num}]"

    return f"Ранг {rank_tier}"


def get_hero_name(hero_id):
    """Получает название героя по ID"""
    return HERO_NAMES.get(hero_id, f"Герой {hero_id}")


# ============================================
# FLASK-LOGIN
# ============================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С API
# ============================================

def parse_steam_id(steam_input):
    """Конвертирует различные форматы Steam ID в Account ID"""
    if not steam_input:
        return None

    steam_input = steam_input.strip()

    if 'steamcommunity.com' in steam_input:
        if '/id/' in steam_input:
            custom_url = steam_input.split('/id/')[-1].strip('/')
            try:
                response = requests.get(f"{app.config['OPENDOTA_API_BASE']}/players/{custom_url}", timeout=5)
                if response.status_code == 200:
                    return str(response.json()['profile']['account_id'])
            except:
                pass
        elif '/profiles/' in steam_input:
            steam64 = steam_input.split('/profiles/')[-1].strip('/')
            if steam64.isdigit() and len(steam64) == 17:
                return str(int(steam64) - 76561197960265728)

    if len(steam_input) == 17 and steam_input.isdigit():
        return str(int(steam_input) - 76561197960265728)

    if steam_input.isdigit():
        return steam_input

    try:
        response = requests.get(f"{app.config['OPENDOTA_API_BASE']}/players/{steam_input}", timeout=5)
        if response.status_code == 200:
            return str(response.json()['profile']['account_id'])
    except:
        pass

    return None


def get_player_mmr(steam_account_id):
    """Получает MMR игрока"""
    base_url = app.config['OPENDOTA_API_BASE']
    try:
        response = requests.get(f"{base_url}/players/{steam_account_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            rank_tier = data.get('rank_tier', 0)
            leaderboard = data.get('leaderboard_rank', 0)

            solo_mmr = data.get('solo_competitive_rank')
            if solo_mmr and solo_mmr > 0:
                return solo_mmr, rank_tier, leaderboard

            competitive_rank = data.get('competitive_rank')
            if competitive_rank and competitive_rank > 0:
                return competitive_rank, rank_tier, leaderboard

            mmr_estimate = data.get('mmr_estimate', {})
            if isinstance(mmr_estimate, dict):
                estimate = mmr_estimate.get('estimate', 0)
                if estimate > 0:
                    return estimate, rank_tier, leaderboard

            if leaderboard and leaderboard > 0:
                return max(6000, 6500 - leaderboard), rank_tier, leaderboard

            if rank_tier > 0:
                return estimate_mmr_from_rank(rank_tier), rank_tier, leaderboard
    except:
        pass
    return 0, 0, 0


def estimate_mmr_from_rank(rank_tier):
    """Примерный MMR по рангу"""
    medal = rank_tier // 10
    stars = rank_tier % 10
    base_mmr = {1: 150, 2: 770, 3: 1540, 4: 2310, 5: 3080, 6: 3850, 7: 4620, 8: 5420}
    if medal in base_mmr:
        return base_mmr[medal] + stars * 155
    return 0


def get_player_data(steam_account_id):
    """Получает полные данные игрока"""
    try:
        base_url = app.config['OPENDOTA_API_BASE']
        player_response = requests.get(f"{base_url}/players/{steam_account_id}", timeout=10)
        if player_response.status_code != 200:
            return None
        player_data = player_response.json()

        wl_data = {'win': 0, 'lose': 0}
        try:
            wl_response = requests.get(f"{base_url}/players/{steam_account_id}/wl", timeout=5)
            if wl_response.status_code == 200:
                wl_data = wl_response.json()
        except:
            pass

        matches_data = []
        try:
            matches_response = requests.get(f"{base_url}/players/{steam_account_id}/recentMatches", timeout=5)
            if matches_response.status_code == 200:
                matches_data = matches_response.json()
        except:
            pass

        heroes_data = []
        try:
            heroes_response = requests.get(f"{base_url}/players/{steam_account_id}/heroes", timeout=5)
            if heroes_response.status_code == 200:
                heroes_data = heroes_response.json()
        except:
            pass

        return {'player': player_data, 'wl': wl_data, 'recent_matches': matches_data,
                'heroes': heroes_data[:5] if heroes_data else []}
    except:
        return None


def calculate_mmr_change(recent_matches):
    """Рассчитывает изменение MMR за 20 матчей"""
    if not recent_matches:
        return 0, 0, 0

    total_change = 0
    wins = 0
    losses = 0

    for match in recent_matches[:20]:
        if match.get('radiant_win') is not None and match.get('player_slot') is not None:
            is_win = (match['player_slot'] < 128) == match['radiant_win']
            if is_win:
                total_change += 25
                wins += 1
            else:
                total_change -= 25
                losses += 1

    return total_change, wins, losses


def update_player_data(user):
    """Обновляет данные игрока в базе данных"""
    if not user.steam_id:
        return

    player_data = get_player_data(user.steam_id)
    if not player_data:
        flash('Не удалось получить данные игрока', 'danger')
        return

    mmr, rank_tier, leaderboard = get_player_mmr(user.steam_id)
    if mmr == 0:
        mmr = player_data['player'].get('solo_competitive_rank') or player_data['player'].get('competitive_rank') or 0
    if rank_tier == 0:
        rank_tier = player_data['player'].get('rank_tier', 0)

    rank_name = get_rank_name(rank_tier)
    mmr_change, recent_wins, recent_losses = calculate_mmr_change(player_data['recent_matches'])

    winrate = 0
    total_games = 0
    if player_data['wl']:
        wins = player_data['wl'].get('win', 0)
        losses = player_data['wl'].get('lose', 0)
        total_games = wins + losses
        if total_games > 0:
            winrate = round((wins / total_games) * 100, 1)

    stats = PlayerStats.query.filter_by(user_id=user.id).first()
    if not stats:
        stats = PlayerStats(user_id=user.id)

    stats.mmr_estimate = mmr
    stats.winrate = winrate
    stats.total_games = total_games
    stats.rank_tier = rank_tier
    stats.leaderboard_rank = leaderboard

    if player_data['heroes']:
        stats.favorite_heroes = json.dumps([h['hero_id'] for h in player_data['heroes'][:3]])

    stats.last_updated = datetime.utcnow()
    stats.extra_data = json.dumps({
        'rank_name': rank_name,
        'mmr_change': mmr_change,
        'recent_wins': recent_wins,
        'recent_losses': recent_losses
    })

    db.session.add(stats)

    if player_data['recent_matches']:
        MatchHistory.query.filter_by(user_id=user.id).delete()
        for match in player_data['recent_matches'][:20]:
            is_win = None
            if match.get('radiant_win') is not None and match.get('player_slot') is not None:
                is_win = (match['player_slot'] < 128) == match['radiant_win']

            new_match = MatchHistory(
                user_id=user.id,
                match_id=str(match.get('match_id')),
                hero_id=match.get('hero_id', 0),
                hero_name=get_hero_name(match.get('hero_id', 0)),
                kills=match.get('kills', 0),
                deaths=match.get('deaths', 0),
                assists=match.get('assists', 0),
                win=is_win if is_win is not None else False,
                game_mode=match.get('game_mode'),
                duration=match.get('duration', 0),
                match_date=datetime.fromtimestamp(match.get('start_time', 0)) if match.get('start_time') else None
            )
            db.session.add(new_match)

    db.session.commit()


# ============================================
# ФУНКЦИИ АНАЛИЗА РЕПЛЕЕВ
# ============================================

def analyze_replay_file(filepath):
    """Анализ файла реплея Dota 2"""
    try:
        file_size = os.path.getsize(filepath)

        if file_size < 10000:
            return {'error': 'Файл слишком маленький для реплея'}

        with open(filepath, 'rb') as f:
            content = f.read()

        result = {
            'file_size': file_size,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'match_id': '',
            'game_mode': 'Неизвестно',
            'duration': 'Неизвестно',
            'winner': 'Неизвестно',
            'players': [],
            'players_count': 0,
            'total_kills': 0,
            'status': 'success'
        }

        # 1. Ищем Match ID
        match_patterns = [
            rb'match_id[^0-9]*(\d{9,10})',
            rb'(\d{10})',
            rb'(\d{9})',
        ]
        for pattern in match_patterns:
            matches = re.findall(pattern, content)
            if matches:
                result['match_id'] = matches[0].decode('utf-8', errors='ignore')
                break

        # 2. Ищем режим игры
        game_modes = {
            1: 'All Pick', 2: 'Captains Mode', 3: 'Random Draft',
            4: 'Single Draft', 5: 'All Random', 22: 'Ranked All Pick',
            23: 'Turbo Mode'
        }
        mode_matches = re.findall(rb'game_mode[":\s]*(\d+)', content)
        if mode_matches:
            mode_id = int(mode_matches[0])
            result['game_mode'] = game_modes.get(mode_id, f'Режим {mode_id}')

        # 3. Ищем длительность
        duration_matches = re.findall(rb'duration[":\s]*(\d+)', content)
        if duration_matches:
            seconds = int(duration_matches[0])
            if 60 < seconds < 7200:
                minutes = seconds // 60
                secs = seconds % 60
                result['duration'] = f"{minutes}:{secs:02d}"

        # 4. Определяем победителя
        if re.findall(rb'radiant_win[":\s]*(true|1)', content, re.IGNORECASE):
            result['winner'] = 'Radiant'
        elif re.findall(rb'radiant_win[":\s]*(false|0)', content, re.IGNORECASE):
            result['winner'] = 'Dire'

        # 5. Ищем героев
        hero_ids = set()
        hero_matches = re.findall(rb'hero_id[":\s]*(\d+)', content)
        for match in hero_matches:
            try:
                hid = int(match)
                if 1 <= hid <= 200:
                    hero_ids.add(hid)
            except:
                pass

        # Ищем по именам героев
        if not hero_ids:
            for hero_id, hero_name in HERO_NAMES.items():
                if hero_name.encode('utf-8') in content:
                    hero_ids.add(hero_id)

        result['players_count'] = min(len(hero_ids), 10)

        for hero_id in list(hero_ids)[:10]:
            hero_name = get_hero_name(hero_id)
            result['players'].append({
                'hero_id': hero_id,
                'hero_name': hero_name
            })

        # 6. Ищем K/D/A
        player_pattern = rb'kills[":\s]*(\d+).*?deaths[":\s]*(\d+).*?assists[":\s]*(\d+)'
        player_matches = re.findall(player_pattern, content)
        for pm in player_matches[:10]:
            try:
                result['total_kills'] += int(pm[0])
            except:
                pass

        if not result['match_id'] and not hero_ids:
            result['status'] = 'partial'
            result['note'] = 'Данные не найдены, но файл сохранен'

        return result

    except Exception as e:
        return {'error': str(e), 'status': 'error'}


# ============================================
# МАРШРУТЫ
# ============================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Это имя пользователя уже занято', 'danger')
            return render_template('register.html', form=form)

        if User.query.filter_by(email=form.email.data).first():
            flash('Этот email уже зарегистрирован', 'danger')
            return render_template('register.html', form=form)

        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)

        if form.steam_id.data:
            steam_account_id = parse_steam_id(form.steam_id.data)
            if steam_account_id:
                user.steam_id = steam_account_id

        db.session.add(user)
        db.session.commit()

        if user.steam_id:
            update_player_data(user)

        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Неверный email или пароль', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    stats = PlayerStats.query.filter_by(user_id=current_user.id).first()
    recent_matches = MatchHistory.query.filter_by(user_id=current_user.id) \
        .order_by(MatchHistory.match_date.desc()).limit(20).all()

    extra_data = {}
    if stats and stats.extra_data:
        try:
            extra_data = json.loads(stats.extra_data)
        except:
            pass

    favorite_heroes = []
    if stats and stats.favorite_heroes:
        try:
            hero_ids = json.loads(stats.favorite_heroes)
            for hero_id in hero_ids:
                favorite_heroes.append({'id': hero_id, 'name': get_hero_name(hero_id)})
        except:
            pass

    return render_template('dashboard.html',
                           stats=stats,
                           recent_matches=recent_matches,
                           extra_data=extra_data,
                           favorite_heroes=favorite_heroes)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data

        if form.steam_id.data and form.steam_id.data != current_user.steam_id:
            steam_id = parse_steam_id(form.steam_id.data)
            if steam_id:
                current_user.steam_id = steam_id
                db.session.commit()
                update_player_data(current_user)
                flash('Steam ID обновлен и данные загружены!', 'success')
            else:
                flash('Неверный формат Steam ID', 'danger')

        if form.avatar.data:
            filename = secure_filename(f"avatar_{current_user.id}_{form.avatar.data.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.avatar.data.save(filepath)
            current_user.avatar = filename
            flash('Аватар обновлен!', 'success')

        db.session.commit()
        flash('Профиль обновлен!', 'success')
        return redirect(url_for('profile'))

    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.steam_id.data = current_user.steam_id

    avatar_url = None
    if current_user.avatar:
        avatar_url = url_for('static', filename='uploads/' + current_user.avatar)

    return render_template('profile.html', form=form, avatar_url=avatar_url)


@app.route('/refresh-stats')
@login_required
def refresh_stats():
    if not current_user.steam_id:
        flash('Сначала укажите Steam ID в профиле', 'warning')
        return redirect(url_for('profile'))

    update_player_data(current_user)
    flash('Статистика обновлена!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/export-stats')
@login_required
def export_stats():
    matches = MatchHistory.query.filter_by(user_id=current_user.id) \
        .order_by(MatchHistory.match_date.desc()).all()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Дата', 'Герой', 'Kills', 'Deaths', 'Assists', 'KDA', 'Результат', 'Длительность'])

    for match in matches:
        kda = round((match.kills + match.assists) / max(match.deaths, 1),
                    2) if match.deaths > 0 else match.kills + match.assists
        cw.writerow([
            match.match_date.strftime('%d.%m.%Y %H:%M') if match.match_date else '',
            match.hero_name or f'Hero {match.hero_id}',
            match.kills,
            match.deaths,
            match.assists,
            kda,
            'Win' if match.win else 'Loss',
            f'{match.duration // 60}min' if match.duration else ''
        ])

    output = Response(si.getvalue(), mimetype='text/csv; charset=utf-8')
    output.headers["Content-Disposition"] = f"attachment; filename=dota_stats_{current_user.username}.csv"
    return output


@app.route('/upload-replay', methods=['GET', 'POST'])
@login_required
def upload_replay():
    if request.method == 'POST':
        if 'replay' not in request.files:
            flash('Файл не выбран', 'danger')
            return redirect(url_for('upload_replay'))

        file = request.files['replay']
        if file.filename == '':
            flash('Файл не выбран', 'danger')
            return redirect(url_for('upload_replay'))

        if not file.filename.endswith('.dem'):
            flash('Поддерживаются только .dem файлы реплеев Dota 2', 'danger')
            return redirect(url_for('upload_replay'))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(f"replay_{current_user.id}_{timestamp}.dem")
        replay_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'replays')
        os.makedirs(replay_dir, exist_ok=True)
        filepath = os.path.join(replay_dir, filename)
        file.save(filepath)

        print(f"\n=== АНАЛИЗ РЕПЛЕЯ ===")
        print(f"Файл: {file.filename}")
        print(f"Размер: {os.path.getsize(filepath)} байт")

        analysis = analyze_replay_file(filepath)
        print(f"Результат: {analysis}")
        print("====================\n")

        replay = Replay(
            user_id=current_user.id,
            filename=filename,
            original_filename=file.filename,
            file_size=os.path.getsize(filepath),
            match_id=analysis.get('match_id', ''),
            players_count=analysis.get('players_count', 0),
            analysis_data=json.dumps(analysis),
            analyzed=True
        )
        db.session.add(replay)
        db.session.commit()

        if 'error' in analysis:
            flash(f'Реплей сохранен (ошибка анализа: {analysis["error"]})', 'warning')
        else:
            flash(
                f'Реплей загружен и проанализирован! Найдено героев: {analysis.get("players_count", 0)}, ID матча: {analysis.get("match_id", "не найден")}',
                'success')

        return redirect(url_for('my_replays'))

    return render_template('upload_replay.html')


@app.route('/my-replays')
@login_required
def my_replays():
    replays = Replay.query.filter_by(user_id=current_user.id) \
        .order_by(Replay.uploaded_at.desc()).all()

    # Парсим JSON для каждого реплея
    parsed_replays = []
    for replay in replays:
        replay_dict = {
            'id': replay.id,
            'filename': replay.filename,
            'original_filename': replay.original_filename,
            'file_size': replay.file_size,
            'match_id': replay.match_id,
            'players_count': replay.players_count,
            'uploaded_at': replay.uploaded_at,
            'analyzed': replay.analyzed,
            'analysis_data': {}
        }

        # Парсим analysis_data
        if replay.analysis_data:
            try:
                # Пробуем загрузить как JSON
                analysis = json.loads(replay.analysis_data)
                replay_dict['analysis_data'] = analysis
            except:
                try:
                    # Если это строка с экранированными символами
                    import ast
                    analysis = ast.literal_eval(replay.analysis_data)
                    replay_dict['analysis_data'] = analysis
                except:
                    # Если ничего не работает, оставляем как есть
                    replay_dict['analysis_data'] = {'raw': replay.analysis_data}

        parsed_replays.append(replay_dict)

    return render_template('replays.html', replays=parsed_replays)


@app.route('/download-replay/<int:replay_id>')
@login_required
def download_replay(replay_id):
    replay = Replay.query.get_or_404(replay_id)
    if replay.user_id != current_user.id:
        flash('Нет доступа', 'danger')
        return redirect(url_for('my_replays'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'replays', replay.filename)
    if not os.path.exists(filepath):
        flash('Файл не найден', 'danger')
        return redirect(url_for('my_replays'))

    return send_file(filepath, download_name=replay.original_filename, as_attachment=True)


@app.route('/delete-replay/<int:replay_id>')
@login_required
def delete_replay(replay_id):
    replay = Replay.query.get_or_404(replay_id)
    if replay.user_id != current_user.id:
        flash('Нет доступа', 'danger')
        return redirect(url_for('my_replays'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'replays', replay.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(replay)
    db.session.commit()
    flash('Реплей удален', 'success')
    return redirect(url_for('my_replays'))


@app.route('/api/player/<steam_id>')
def api_player_data(steam_id):
    """API для получения данных игрока"""
    account_id = parse_steam_id(steam_id)
    if not account_id:
        return jsonify({'error': 'Invalid Steam ID'}), 400

    player_data = get_player_data(account_id)
    if not player_data:
        return jsonify({'error': 'Player not found'}), 404

    mmr, rank_tier, _ = get_player_mmr(account_id)
    rank_name = get_rank_name(rank_tier)
    mmr_change, wins, losses = calculate_mmr_change(player_data['recent_matches'])

    return jsonify({
        'steam_id': account_id,
        'mmr': mmr,
        'rank': rank_name,
        'winrate': round((player_data['wl'].get('win', 0) / max(
            player_data['wl'].get('win', 0) + player_data['wl'].get('lose', 0), 1)) * 100, 1),
        'mmr_change': mmr_change,
        'recent_wins': wins,
        'recent_losses': losses
    })


# ============================================
# ЗАПУСК
# ============================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'replays'), exist_ok=True)
        load_hero_names()
        print(f"✅ База данных создана")
        print(f"✅ Героев загружено: {len(HERO_NAMES)}")

    print("=" * 50)
    print("🚀 Сервер запущен!")
    print("📍 http://localhost:5000")
    print("=" * 50)

    app.run(debug=True, host='0.0.0.0', port=5000)

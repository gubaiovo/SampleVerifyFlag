import os
import json
import yaml
from flask import (
    Flask, 
    render_template, 
    request, 
    jsonify, 
    session, 
    redirect, 
    url_for, 
    send_from_directory,
    make_response
)
from datetime import datetime

APP_FILE_PATH = os.path.abspath(__file__)
APP_DIR = os.path.dirname(APP_FILE_PATH)
PROJECT_ROOT = os.path.dirname(APP_DIR)

app = Flask(__name__, template_folder=os.path.join(APP_DIR, 'templates'))
app.secret_key = 'a_very_secret_key_for_ctf_platform'
app.jinja_env.add_extension('jinja2.ext.do')

CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.yaml')
USERS_DIR = os.path.join(PROJECT_ROOT, 'data/users')
ZIPS_DIR = os.path.join(PROJECT_ROOT, 'data/challenge/zips')
EXPS_DIR = os.path.join(PROJECT_ROOT, 'data/challenge/exps')

os.makedirs(USERS_DIR, exist_ok=True)
os.makedirs(ZIPS_DIR, exist_ok=True)
os.makedirs(EXPS_DIR, exist_ok=True)


def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_user_progress(username):
    filepath = os.path.join(USERS_DIR, f"{username}.json")
    if not os.path.exists(filepath):
        new_user_data = {"username": username, "solved": []}
        save_user_progress(username, new_user_data)
        return new_user_data
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content: return {"username": username, "solved": []}
            return json.loads(content)
    except json.JSONDecodeError:
        return {"username": username, "solved": []}

def save_user_progress(username, data):
    filepath = os.path.join(USERS_DIR, f"{username}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if not username:
            return render_template('login.html', error="用户名不能为空")
        if not username.isalnum():
            return render_template('login.html', error="用户名只能包含字母和数字")

        session['username'] = username
        get_user_progress(username) 
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def index():
    if 'username' not in session: return redirect(url_for('login'))
    config = load_config()
    if config.get('weeks'):
        return redirect(url_for('show_week', week_id=config['weeks'][0]['id']))
    return "Config Error: No weeks found.", 500

@app.route('/week/<week_id>')
def show_week(week_id):
    if 'username' not in session: return redirect(url_for('login'))
    username = session['username']
    config = load_config()
    
    current_week = next((w for w in config.get('weeks', []) if w['id'] == week_id), None)
    if not current_week: return "Week not found", 404

    user_data = get_user_progress(username)
    solved_ids = [s['chal_id'] for s in user_data.get('solved', [])]

    return render_template('index.html', 
                           site_title=config.get('website_title', 'CTF'),
                           weeks=config.get('weeks', []), 
                           current_week=current_week,
                           username=username,
                           solved_ids=solved_ids)
    
@app.route('/api/verify_flag', methods=['POST'])
def verify_flag():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': '未登录'}), 401

    data = request.json
    if data is None:
        return jsonify({'status': 'error', 'message': '无效的请求'}), 400
    
    user_flag = data.get('flag', '').strip()
    chal_id = data.get('chal_id')
    week_id = data.get('week_id')
    username = session['username']

    config = load_config()
    
    target_week = next((w for w in config.get('weeks', []) if w['id'] == week_id), None)
    if not target_week:
        return jsonify({'status': 'error', 'message': 'Week ID 错误'})

    target_chal = next((c for c in target_week.get('flag_challenges', []) if c['id'] == chal_id), None)
    if not target_chal:
        return jsonify({'status': 'error', 'message': '题目 ID 错误'})

    if user_flag == target_chal['flag']:
        user_data = get_user_progress(username)
        
        if not any(s['chal_id'] == chal_id for s in user_data.get('solved', [])):
            if 'solved' not in user_data:
                user_data['solved'] = []
            user_data['solved'].append({
                "week_id": week_id,
                "chal_id": chal_id,
                "chal_name": target_chal['name'],
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            save_user_progress(username, user_data)

        exp_link = url_for('get_exp_file', filename=target_chal['exp_file'])
        return jsonify({'status': 'success', 'exp_link': exp_link})
    else:
        return jsonify({'status': 'error', 'message': 'Flag 错误'})

@app.route('/admin/stats')
def stats():
    config = load_config()
    admin_user = config.get('admin_username', '')
    if session.get('username', '') != admin_user:
        return "You are not authorized to access this page.", 403
    
    all_users_data = []
    for filename in os.listdir(USERS_DIR):
        if filename.endswith('.json'):
            username = filename[:-5]
            all_users_data.append(get_user_progress(username))
    
    resp = make_response(render_template('stats.html', 
                                         config=config, 
                                         users=all_users_data
                                         ))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/zip/<filename>')
def get_zip_file(filename):
    return send_from_directory(ZIPS_DIR, filename, as_attachment=True)

@app.route('/exp/<filename>')
def get_exp_file(filename):
    if 'username' not in session:
        return "Access Denied: Login required", 403
    username = session['username']
    config = load_config()
    admin_user = config.get('admin_username', '')
    if username == admin_user:
        return send_from_directory(EXPS_DIR, filename, as_attachment=True)
    user_data = get_user_progress(username)
    solved_ids = {s['chal_id'] for s in user_data.get('solved', [])}
    is_allowed = False
    for week in config.get('weeks', []):
        for chal in week.get('flag_challenges', []):
            if chal.get('exp_file') == filename and chal['id'] in solved_ids:
                is_allowed = True
                break
        if is_allowed: break
    
    if is_allowed:
        return send_from_directory(EXPS_DIR, filename, as_attachment=True)
    else:
        return "Access Denied: You must solve the challenge first.", 403
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

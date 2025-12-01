from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Task
from config import Config
import requests
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        city = request.form.get('city', 'Kathmandu')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email, preferred_city=city)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    city = request.args.get('city', current_user.preferred_city)
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
    
    # Basic weather data (TODO: Add full API integration)
    weather_data = get_weather(city)
    
    nepal_cities = [
        'Kathmandu', 'Pokhara', 'Lalitpur', 'Bhaktapur', 'Biratnagar'
    ]
    
    return render_template('dashboard.html', 
                         tasks=tasks, 
                         weather=weather_data,
                         current_city=city,
                         cities=nepal_cities)


@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    task_name = request.form.get('task_name')
    
    if task_name:
        # TODO: Add AI analysis here
        task = Task(
            user_id=current_user.id,
            task_name=task_name
        )
        db.session.add(task)
        db.session.commit()
        flash('Task added!', 'success')
    
    return redirect(url_for('dashboard'))


@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
        flash('Task deleted!', 'info')
    return redirect(url_for('dashboard'))


@app.route('/toggle_task/<int:task_id>')
@login_required
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == current_user.id:
        task.status = 'completed' if task.status == 'pending' else 'pending'
        db.session.commit()
    return redirect(url_for('dashboard'))


def get_weather(city):
    """Basic weather fetching - will expand later"""
    api_key = app.config['OPENWEATHER_API_KEY']
    
    try:
        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {
            'q': f'{city},NP',
            'appid': api_key,
            'units': 'metric'
        }
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        weather = {
            'city': city,
            'temp': round(data['main']['temp']),
            'description': data['weather'][0]['description'].title(),
            'humidity': data['main']['humidity'],
            'condition': data['weather'][0]['main'].lower()
        }
        return weather
    except Exception as e:
        print(f"Weather API Error: {e}")
        return None


# Initialize database
with app.app_context():
    db.create_all()
    print("Database tables created!")


if __name__ == '__main__':
    app.run(debug=True)
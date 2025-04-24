from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import time
from datetime import datetime
import os
import json

auth_bp = Blueprint('auth', __name__)

def is_logged_in():
    """Check if user is logged in."""
    return 'user_id' in session

def get_current_user():
    """Get current user data."""
    if is_logged_in():
        user_id = session['user_id']
        users = current_app.config['users']
        if user_id in users:
            return users[user_id]
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and logic."""
    if is_logged_in():
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        users = current_app.config['users']
        
        # Check if username exists and password is correct
        for user_id, user_data in users.items():
            if user_data['username'] == username:
                if check_password_hash(user_data['password'], password):
                    session.permanent = True
                    session['user_id'] = user_id
                    session['username'] = username
                    flash('Login successful!', 'success')
                    return redirect(url_for('main.index'))
                else:
                    flash('Invalid password. Please try again.', 'danger')
                    break
        else:
            flash('Username not found.', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration page and logic."""
    if is_logged_in():
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        users = current_app.config['users']
        save_users = current_app.config['save_users']
        
        # Form validation
        if not username or not password:
            flash('Username and password are required.', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            # Check if username already exists
            for user_data in users.values():
                if user_data['username'] == username:
                    flash('Username already exists. Please choose another.', 'danger')
                    break
            else:
                # Create new user
                user_id = str(int(time.time()))  # Simple unique ID
                users[user_id] = {
                    'username': username,
                    'password': generate_password_hash(password),
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'decks': []
                }
                save_users()
                
                # Log in the new user
                session.permanent = True
                session['user_id'] = user_id
                session['username'] = username
                
                flash('Account created successfully!', 'success')
                return redirect(url_for('main.index'))
    
    return render_template('signup.html')

@auth_bp.route('/logout')
def logout():
    """Log user out."""
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/user/profile')
def user_profile():
    """User profile page."""
    if not is_logged_in():
        flash('Please log in to view your profile.', 'warning')
        return redirect(url_for('auth.login'))
    
    user = get_current_user()
    meta_stats = current_app.config['meta_stats']
    
    # Get user's decks
    user_decks = []
    for deck_id in user.get('decks', []):
        try:
            # Load deck data
            with open(f'decks/{deck_id}.json', 'r') as f:
                deck_data = json.load(f)
                
                # Get win rate from meta stats if available
                win_rate = None
                deck_name = deck_data.get('name')
                if deck_name in meta_stats["decks"]:
                    stats = meta_stats["decks"][deck_name]
                    if stats["total_battles"] > 0:
                        win_rate = (stats["wins"] / stats["total_battles"]) * 100
                
                user_decks.append({
                    'name': deck_name,
                    'filename': f"{deck_id}.json",
                    'types': deck_data.get('deck_types', []),
                    'card_count': len(deck_data.get('cards', [])),
                    'win_rate': round(win_rate, 1) if win_rate is not None else None
                })
        except Exception as e:
            print(f"Error loading deck {deck_id}: {e}")
    
    # Get user's battle history
    battle_history = current_app.config['battle_history']
    user_battles = []
    current_username = user['username']
    for battle in battle_history:
        if battle.get('player1') == current_username or battle.get('player2') == current_username:
            user_battles.append(battle)
    
    return render_template('user_profile.html', user=user, decks=user_decks, battles=user_battles)

@auth_bp.route('/user/settings', methods=['GET', 'POST'])
def user_settings():
    """User settings page."""
    if not is_logged_in():
        flash('Please log in to access settings.', 'warning')
        return redirect(url_for('auth.login'))
    
    user = get_current_user()
    save_users = current_app.config['save_users']
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate current password
        if not check_password_hash(user['password'], current_password):
            flash('Current password is incorrect.', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
        else:
            # Update password
            user['password'] = generate_password_hash(new_password)
            save_users()
            flash('Password updated successfully.', 'success')
    
    return render_template('user_settings.html', user=user)
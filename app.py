# ... existing code ...

import logging
import os
from logging.handlers import RotatingFileHandler

# ... existing code ...

# Configure logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=3),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ... existing code ...

@app.route('/')
def index():
    logger.info("Index page accessed")
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        logger.info(f"Login attempt for user: {username}")
        
        if username == os.getenv('ADMIN_USER') and password == os.getenv('ADMIN_PASS'):
            session['logged_in'] = True
            session['username'] = username
            logger.info(f"User {username} logged in successfully")
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            logger.warning(f"Failed login attempt for user: {username}")
            flash('Invalid credentials', 'danger')
    
    return render_template('login.html')

# ... existing code ...

if __name__ == '__main__':
    logger.info("Starting GLPI 10 SQL Generator application")
    logger.info(f"Server running on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', debug=True)
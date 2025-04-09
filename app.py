import os
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import pandas as pd
import io
from datetime import datetime

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "defaultsecret")
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def parse_excel(file_path):
    xls = pd.read_excel(file_path, sheet_name=None)
    sql_outputs = {}
    for aba, df in xls.items():
        if df.empty:
            continue
        df = df.dropna(how='all')
        colunas = ', '.join(df.columns)
        values = ",\n".join(
            df.apply(lambda row: f"({', '.join([repr(v) for v in row.values])})", axis=1)
        )
        sql_outputs[aba] = f"INSERT INTO {aba} ({colunas}) VALUES\n{values};"
    return sql_outputs

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        if user == os.getenv('ADMIN_USER') and pw == os.getenv('ADMIN_PASS'):
            session['user'] = user
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            session['uploaded_file'] = path
            flash('Upload realizado com sucesso.')
            return redirect(url_for('export'))
    return render_template('upload.html')

@app.route('/export')
def export():
    if 'user' not in session or 'uploaded_file' not in session:
        return redirect(url_for('login'))
    sql_outputs = parse_excel(session['uploaded_file'])
    full_sql = "\n\n".join(sql_outputs.values())
    filename = f"glpi_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.sql"
    return send_file(io.BytesIO(full_sql.encode()), mimetype='text/sql', as_attachment=True, download_name=filename)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

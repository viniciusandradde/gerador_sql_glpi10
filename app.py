from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os
import pandas as pd
from datetime import datetime
import io
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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

# Login required decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

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

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # List uploaded files
    files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.endswith('.xlsx') and not filename.startswith('~$'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file_stats = os.stat(file_path)
            files.append({
                'name': filename,
                'size': file_stats.st_size,
                'created': datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return render_template('dashboard.html', files=files)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.xlsx'):
            # Save the file
            filename = f"glpi10_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Validate Excel file
            try:
                excel_file = pd.ExcelFile(file_path)
                required_sheets = ['regras_sla', 'criterios_sla', 'acoes_sla', 'regras_grupo', 'criterios_grupo', 'acoes_grupo']
                missing_sheets = [sheet for sheet in required_sheets if sheet not in excel_file.sheet_names]
                
                if missing_sheets:
                    os.remove(file_path)
                    flash(f"Excel file is missing required sheets: {', '.join(missing_sheets)}", 'danger')
                    return redirect(request.url)
                
                flash('File uploaded successfully!', 'success')
                return redirect(url_for('dashboard'))
            
            except Exception as e:
                os.remove(file_path)
                flash(f'Error validating Excel file: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('Only .xlsx files are allowed', 'danger')
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/export/<filename>', methods=['GET'])
@login_required
def export(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        flash('File not found', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Generate SQL from Excel file
        sql_content, sql_sections = generate_sql(file_path, return_sections=True)
        
        return render_template('export.html', 
                              filename=filename, 
                              sql_content=sql_content,
                              sql_sections=sql_sections)
    
    except Exception as e:
        flash(f'Error generating SQL: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/export_download/<filename>', methods=['GET'])
@login_required
def export_download(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        flash('File not found', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Get module selection from query parameters
        modules = {
            'regras_sla': request.args.get('regras_sla', '1') == '1',
            'criterios_sla': request.args.get('criterios_sla', '1') == '1',
            'acoes_sla': request.args.get('acoes_sla', '1') == '1',
            'regras_grupo': request.args.get('regras_grupo', '1') == '1',
            'criterios_grupo': request.args.get('criterios_grupo', '1') == '1',
            'acoes_grupo': request.args.get('acoes_grupo', '1') == '1',
        }
        
        # Generate SQL from Excel file with module selection
        sql_content = generate_sql(file_path, modules=modules)
        
        # Create in-memory file
        sql_file = io.BytesIO()
        sql_file.write(sql_content.encode('utf-8'))
        sql_file.seek(0)
        
        # Generate SQL filename based on original Excel filename
        sql_filename = f"glpi10_script_{filename.split('_', 1)[1].rsplit('.', 1)[0]}.sql"
        
        return send_file(
            sql_file,
            as_attachment=True,
            download_name=sql_filename,
            mimetype='text/plain'
        )
    
    except Exception as e:
        flash(f'Error generating SQL: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

def generate_sql(excel_path, modules=None, return_sections=False):
    """Generate SQL statements from Excel file"""
    if modules is None:
        modules = {
            'regras_sla': True,
            'criterios_sla': True,
            'acoes_sla': True,
            'regras_grupo': True,
            'criterios_grupo': True,
            'acoes_grupo': True,
        }
    
    sql_parts = []
    sql_sections = {}
    
    # Add header with timestamp
    header = f"""-- GLPI 10 SQL Script
-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Generator: GLPI 10 SQL Generator

"""
    sql_parts.append(header)
    sql_sections['header'] = header
    
    # Read Excel sheets
    excel_file = pd.ExcelFile(excel_path)
    
    # Process regras_sla sheet
    if 'regras_sla' in excel_file.sheet_names and modules['regras_sla']:
        df = pd.read_excel(excel_file, 'regras_sla')
        if not df.empty:
            section = "\n-- SLA Rules\n"
            section += "INSERT INTO `glpi_rules` (`id`, `name`, `description`, `match`, `is_active`, `sub_type`, `ranking`, `uuid`) VALUES\n"
            
            rows = []
            for index, row in df.iterrows():
                rows.append(f"({row['id']}, '{row['name']}', '{row['description']}', '{row['match']}', {row['is_active']}, '{row['sub_type']}', {row['ranking']}, '{row['uuid']}')")
            
            section += ",\n".join(rows) + ";\n"
            sql_parts.append(section)
            sql_sections['regras_sla'] = section
    
    # Process criterios_sla sheet
    if 'criterios_sla' in excel_file.sheet_names and modules['criterios_sla']:
        df = pd.read_excel(excel_file, 'criterios_sla')
        if not df.empty:
            section = "\n-- SLA Criteria\n"
            section += "INSERT INTO `glpi_rulecriterias` (`id`, `rules_id`, `criteria`, `condition`, `pattern`) VALUES\n"
            
            rows = []
            for index, row in df.iterrows():
                rows.append(f"({row['id']}, {row['rules_id']}, '{row['criteria']}', {row['condition']}, '{row['pattern']}')")
            
            section += ",\n".join(rows) + ";\n"
            sql_parts.append(section)
            sql_sections['criterios_sla'] = section
    
    # Process acoes_sla sheet
    if 'acoes_sla' in excel_file.sheet_names and modules['acoes_sla']:
        df = pd.read_excel(excel_file, 'acoes_sla')
        if not df.empty:
            section = "\n-- SLA Actions\n"
            section += "INSERT INTO `glpi_ruleactions` (`id`, `rules_id`, `action_type`, `field`, `value`) VALUES\n"
            
            rows = []
            for index, row in df.iterrows():
                rows.append(f"({row['id']}, {row['rules_id']}, '{row['action_type']}', '{row['field']}', '{row['value']}')")
            
            section += ",\n".join(rows) + ";\n"
            sql_parts.append(section)
            sql_sections['acoes_sla'] = section
    
    # Process regras_grupo sheet
    if 'regras_grupo' in excel_file.sheet_names and modules['regras_grupo']:
        df = pd.read_excel(excel_file, 'regras_grupo')
        if not df.empty:
            section = "\n-- Group Rules\n"
            section += "INSERT INTO `glpi_rules` (`id`, `name`, `description`, `match`, `is_active`, `sub_type`, `ranking`, `uuid`) VALUES\n"
            
            rows = []
            for index, row in df.iterrows():
                rows.append(f"({row['id']}, '{row['name']}', '{row['description']}', '{row['match']}', {row['is_active']}, '{row['sub_type']}', {row['ranking']}, '{row['uuid']}')")
            
            section += ",\n".join(rows) + ";\n"
            sql_parts.append(section)
            sql_sections['regras_grupo'] = section
    
    # Process criterios_grupo sheet
    if 'criterios_grupo' in excel_file.sheet_names and modules['criterios_grupo']:
        df = pd.read_excel(excel_file, 'criterios_grupo')
        if not df.empty:
            section = "\n-- Group Criteria\n"
            section += "INSERT INTO `glpi_rulecriterias` (`id`, `rules_id`, `criteria`, `condition`, `pattern`) VALUES\n"
            
            rows = []
            for index, row in df.iterrows():
                rows.append(f"({row['id']}, {row['rules_id']}, '{row['criteria']}', {row['condition']}, '{row['pattern']}')")
            
            section += ",\n".join(rows) + ";\n"
            sql_parts.append(section)
            sql_sections['criterios_grupo'] = section
    
    # Process acoes_grupo sheet
    if 'acoes_grupo' in excel_file.sheet_names and modules['acoes_grupo']:
        df = pd.read_excel(excel_file, 'acoes_grupo')
        if not df.empty:
            section = "\n-- Group Actions\n"
            section += "INSERT INTO `glpi_ruleactions` (`id`, `rules_id`, `action_type`, `field`, `value`) VALUES\n"
            
            rows = []
            for index, row in df.iterrows():
                rows.append(f"({row['id']}, {row['rules_id']}, '{row['action_type']}', '{row['field']}', '{row['value']}')")
            
            section += ",\n".join(rows) + ";\n"
            sql_parts.append(section)
            sql_sections['acoes_grupo'] = section
    
    # Combine all SQL parts
    sql_content = "".join(sql_parts)
    
    if return_sections:
        return sql_content, sql_sections
    else:
        return sql_content

@app.route('/generate_template', methods=['GET'])
@login_required
def generate_template():
    try:
        # Create output path for the template
        template_filename = f"glpi10_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        template_path = os.path.join(app.config['UPLOAD_FOLDER'], template_filename)
        
        # Create a Pandas Excel writer
        writer = pd.ExcelWriter(template_path, engine='xlsxwriter')
        
        # Create regras_sla sheet
        regras_sla_columns = ['id', 'name', 'description', 'match', 'is_active', 'sub_type', 'ranking', 'uuid']
        regras_sla_df = pd.DataFrame(columns=regras_sla_columns)
        regras_sla_df.loc[0] = [1, 'Example SLA Rule', 'Description of SLA rule', 'AND', 1, 'RuleTicket', 1, 'unique-uuid-1']
        regras_sla_df.to_excel(writer, sheet_name='regras_sla', index=False)
        
        # Create criterios_sla sheet
        criterios_sla_columns = ['id', 'rules_id', 'criteria', 'condition', 'pattern']
        criterios_sla_df = pd.DataFrame(columns=criterios_sla_columns)
        criterios_sla_df.loc[0] = [1, 1, 'itilcategories_id', 6, '1']
        criterios_sla_df.to_excel(writer, sheet_name='criterios_sla', index=False)
        
        # Create acoes_sla sheet
        acoes_sla_columns = ['id', 'rules_id', 'action_type', 'field', 'value']
        acoes_sla_df = pd.DataFrame(columns=acoes_sla_columns)
        acoes_sla_df.loc[0] = [1, 1, 'assign', 'slas_id', '1']
        acoes_sla_df.to_excel(writer, sheet_name='acoes_sla', index=False)
        
        # Create regras_grupo sheet
        regras_grupo_columns = ['id', 'name', 'description', 'match', 'is_active', 'sub_type', 'ranking', 'uuid']
        regras_grupo_df = pd.DataFrame(columns=regras_grupo_columns)
        regras_grupo_df.loc[0] = [1, 'Example Group Rule', 'Description of group rule', 'AND', 1, 'RuleTicket', 1, 'unique-uuid-2']
        regras_grupo_df.to_excel(writer, sheet_name='regras_grupo', index=False)
        
        # Create criterios_grupo sheet
        criterios_grupo_columns = ['id', 'rules_id', 'criteria', 'condition', 'pattern']
        criterios_grupo_df = pd.DataFrame(columns=criterios_grupo_columns)
        criterios_grupo_df.loc[0] = [1, 1, 'itilcategories_id', 6, '1']
        criterios_grupo_df.to_excel(writer, sheet_name='criterios_grupo', index=False)
        
        # Create acoes_grupo sheet
        acoes_grupo_columns = ['id', 'rules_id', 'action_type', 'field', 'value']
        acoes_grupo_df = pd.DataFrame(columns=acoes_grupo_columns)
        acoes_grupo_df.loc[0] = [1, 1, 'assign', 'groups_id', '1']
        acoes_grupo_df.to_excel(writer, sheet_name='acoes_grupo', index=False)
        
        # Save the Excel file
        writer.close()
        
        logger.info(f"Template Excel file created: {template_filename}")
        flash('Template Excel file created successfully!', 'success')
        
        # Return the file for download
        return send_file(
            template_path,
            as_attachment=True,
            download_name=template_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        flash(f'Error creating template: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    logger.info("Starting GLPI 10 SQL Generator application")
    logger.info(f"Server running on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', debug=True)
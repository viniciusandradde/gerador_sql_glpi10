from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os
import pandas as pd
from datetime import datetime
import io
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import uuid

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
            filename = f"catalogo_servicos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Validate Excel file
            try:
                excel_file = pd.ExcelFile(file_path)
                required_sheets = ['catalogo_servicos']
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
            'categorias': request.args.get('categorias', '1') == '1',
            'slas': request.args.get('slas', '1') == '1',
            'regras_atribuicao': request.args.get('regras_atribuicao', '1') == '1',
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

@app.route('/generate_template', methods=['GET'])
@login_required
def generate_template():
    try:
        # Create output path for the template
        template_filename = f"catalogo_servicos_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        template_path = os.path.join(app.config['UPLOAD_FOLDER'], template_filename)
        
        # Create a Pandas Excel writer
        writer = pd.ExcelWriter(template_path, engine='xlsxwriter')
        workbook = writer.book
        
        # Create catalogo_servicos sheet
        catalogo_columns = ['Categoria', 'ID da Categoria', 'SLA', 'ID do SLA', 'Nome do Grupo', 'ID do Grupo']
        catalogo_df = pd.DataFrame(columns=catalogo_columns)
        
        # Add example data
        example_data = [
            ['Comunicação e Conectividade > Conectividade de Internet > Conectividade de Internet > Bloqueio de Acesso a Sites', 10, '16 horas', 8, 'Segurança da Informação', 2],
            ['Comunicação e Conectividade > Conectividade de Internet > Falha de acesso', 12, '04 horas', 12, 'Suporte N1', 6],
            ['Comunicação e Conectividade > Conectividade de Internet > Liberação de Acesso a Sites', 15, '08 horas', 10, 'Segurança da Informação', 2]
        ]
        
        for i, row in enumerate(example_data):
            catalogo_df.loc[i] = row
            
        catalogo_df.to_excel(writer, sheet_name='catalogo_servicos', index=False)
        
        # Format the catalogo_servicos sheet
        worksheet = writer.sheets['catalogo_servicos']
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
        
        for col_num, value in enumerate(catalogo_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)
        
        # Create organizacao_categorias sheet
        org_cat_columns = ['Categoria Original', 'Categoria nível 1', 'Categoria nível 2', 'Categoria nível 3']
        org_cat_df = pd.DataFrame(columns=org_cat_columns)
        
        # Add example data for category organization
        org_cat_data = [
            ['Comunicação e Conectividade > Conectividade de Internet > Bloqueio de Acesso a Sites', 
             'Comunicação e Conectividade', 'Conectividade de Internet', 'Bloqueio de Acesso a Sites'],
            ['Comunicação e Conectividade > Conectividade de Internet > Falha de acesso', 
             'Comunicação e Conectividade', 'Conectividade de Internet', 'Falha de acesso'],
            ['Comunicação e Conectividade > Serviço de VPN > Configuração de VPN', 
             'Comunicação e Conectividade', 'Serviço de VPN', 'Configuração de VPN']
        ]
        
        for i, row in enumerate(org_cat_data):
            org_cat_df.loc[i] = row
            
        org_cat_df.to_excel(writer, sheet_name='organizacao_categorias', index=False)
        
        # Format the organizacao_categorias sheet
        worksheet = writer.sheets['organizacao_categorias']
        
        # Add header formatting
        for col_num, value in enumerate(org_cat_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 30)
        
        # Add instructions to the sheet
        instruction_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
        worksheet.merge_range('A15:D15', 'Instruções:', workbook.add_format({'bold': True}))
        instructions = [
            '1. Cole suas categorias na coluna A',
            '2. Utilize "Dados > Texto para colunas" no Excel para separar o texto usando ">" como delimitador',
            '3. Use a função "=ARRUMAR()" para remover espaços extras',
            '4. Use "=PRI.MAIUSCULA()" para padronizar o texto com primeiras letras maiúsculas'
        ]
        for i, instruction in enumerate(instructions):
            worksheet.write(15+i, 0, instruction, instruction_format)
            worksheet.merge_range(f'A{15+i+1}:D{15+i+1}', instruction, instruction_format)
        
        # Create regras_categorizacao sheet
        regras_cat_columns = ['id', 'entities_id', 'sub_type', 'ranking', 'name', 'description', 'match', 'is_active', 'comment', 'date_mod', 'is_recursive', 'uuid', 'condition']
        regras_cat_df = pd.DataFrame(columns=regras_cat_columns)
        
        # Add example data for rules
        regras_cat_data = [
            [1001, 0, 'RuleTicket', 1, 'Regra Categoria - Bloqueio de Acesso', 'Atribuição automática para categoria Bloqueio de Acesso', 'AND', 1, '', 'NOW()', 1, 'unique-uuid-1', 0],
            [1002, 0, 'RuleTicket', 2, 'Regra Categoria - Falha de acesso', 'Atribuição automática para categoria Falha de acesso', 'AND', 1, '', 'NOW()', 1, 'unique-uuid-2', 0]
        ]
        
        for i, row in enumerate(regras_cat_data):
            regras_cat_df.loc[i] = row
            
        regras_cat_df.to_excel(writer, sheet_name='regras_categorizacao', index=False)
        
        # Format the regras_categorizacao sheet
        worksheet = writer.sheets['regras_categorizacao']
        
        # Add header formatting
        for col_num, value in enumerate(regras_cat_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 15)
        
        # Add instructions
        worksheet.merge_range('A10:M10', 'Instruções:', workbook.add_format({'bold': True}))
        rule_instructions = [
            '1. Verifique o último ID de regra válido com a consulta: "SELECT id FROM glpi_rules ORDER BY id DESC LIMIT 1"',
            '2. Defina o ID da entidade no campo entities_id (0 para todas as entidades)',
            '3. Defina o ranking (ordem de execução) das regras',
            '4. Cada regra deve ter um UUID único'
        ]
        for i, instruction in enumerate(rule_instructions):
            worksheet.merge_range(f'A{11+i}:M{11+i}', instruction, instruction_format)
        
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

def generate_sql(excel_path, modules=None, return_sections=False):
    """Generate SQL statements from Excel file for GLPI catalog"""
    if modules is None:
        modules = {
            'categorias': True,
            'slas': True,
            'regras_atribuicao': True,
        }
    
    sql_parts = []
    sql_sections = {}
    
    # Add header with timestamp
    header = f"""-- GLPI 10 SQL Script - Catálogo de Serviços
-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Generator: GLPI 10 SQL Generator

"""
    sql_parts.append(header)
    sql_sections['header'] = header
    
    # Read Excel sheet
    try:
        # Check if the file exists
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
        
        # Read the main catalog sheet
        excel_file = pd.ExcelFile(excel_path)
        
        # Check if required sheets exist
        required_sheet = 'catalogo_servicos'
        if required_sheet not in excel_file.sheet_names:
            raise ValueError(f"Required sheet '{required_sheet}' not found in Excel file")
        
        df = pd.read_excel(excel_path, required_sheet)
        
        # Process categories
        if modules['categorias'] and not df.empty:
            section = "\n-- Categorias de Serviços\n"
            
            # Get unique categories
            categories = df[['Categoria', 'ID da Categoria']].drop_duplicates()
            
            if not categories.empty:
                section += "-- Inserção de categorias no GLPI\n"
                section += "INSERT INTO `glpi_itilcategories` (`id`, `name`, `completename`, `comment`, `level`, `knowbaseitemcategories_id`, `users_id`, `groups_id`, `ancestors_cache`, `sons_cache`, `is_helpdeskvisible`, `tickettemplates_id_demand`, `is_incident`, `is_request`, `is_problem`, `is_change`, `date_mod`, `date_creation`) VALUES\n"
                
                category_rows = []
                for _, row in categories.iterrows():
                    # Split the category path
                    cat_parts = row['Categoria'].split(' > ')
                    cat_name = cat_parts[-1]
                    completename = row['Categoria']
                    level = len(cat_parts)
                    
                    # Generate a random UUID for each category
                    random_uuid = str(uuid.uuid4())
                    
                    category_rows.append(f"({row['ID da Categoria']}, '{cat_name}', '{completename}', '', {level}, 0, 0, 0, '', '', 1, 0, 1, 1, 1, 0, NOW(), NOW())")
                
                section += ",\n".join(category_rows) + ";\n"
                sql_parts.append(section)
                sql_sections['categorias'] = section
        
        # Process SLAs
        if modules['slas'] and not df.empty:
            section = "\n-- SLAs\n"
            
            # Get unique SLAs
            slas = df[['SLA', 'ID do SLA']].drop_duplicates()
            
            if not slas.empty:
                section += "-- Inserção de SLAs no GLPI\n"
                section += "INSERT INTO `glpi_slas` (`id`, `name`, `entities_id`, `is_recursive`, `type`, `comment`, `number_time`, `calendars_id`, `date_mod`, `definition_time`, `end_of_working_day`, `date_creation`, `slms_id`) VALUES\n"
                
                sla_rows = []
                for _, row in slas.iterrows():
                    # Parse the SLA time
                    sla_time = row['SLA']
                    time_value = ''.join(filter(str.isdigit, sla_time))
                    time_unit = 'hour' if 'hora' in sla_time.lower() else 'minute'
                    
                    sla_rows.append(f"({row['ID do SLA']}, '{row['SLA']}', 0, 1, 1, '', {time_value}, 1, NOW(), '{time_unit}', 0, NOW(), 1)")
                
                section += ",\n".join(sla_rows) + ";\n"
                sql_parts.append(section)
                sql_sections['slas'] = section
        
        # Process assignment rules
        if modules['regras_atribuicao'] and not df.empty:
            section = "\n-- Regras de Atribuição\n"
            
            # Check if regras_categorizacao sheet exists
            has_rules_sheet = 'regras_categorizacao' in excel_file.sheet_names
            
            # Create rules for each category
            rules_section = "-- Inserção de regras de atribuição no GLPI\n"
            rules_section += "INSERT INTO `glpi_rules` (`id`, `name`, `description`, `match`, `is_active`, `sub_type`, `ranking`, `uuid`, `condition`, `date_mod`, `date_creation`) VALUES\n"
            
            criteria_section = "\n-- Critérios para regras de atribuição\n"
            criteria_section += "INSERT INTO `glpi_rulecriterias` (`id`, `rules_id`, `criteria`, `condition`, `pattern`) VALUES\n"
            
            actions_section = "\n-- Ações para regras de atribuição\n"
            actions_section += "INSERT INTO `glpi_ruleactions` (`id`, `rules_id`, `action_type`, `field`, `value`) VALUES\n"
            
            rule_rows = []
            criteria_rows = []
            action_rows = []
            
            # If we have a rules sheet, use it for rule IDs
            if has_rules_sheet:
                rules_df = pd.read_excel(excel_path, 'regras_categorizacao')
                rule_id_start = rules_df['id'].min() if not rules_df.empty else 1000
            else:
                rule_id_start = 1000  # Default starting ID for rules
                
            criteria_id_start = 2000  # Starting ID for criteria
            action_id_start = 3000  # Starting ID for actions
            
            for _, row in df.iterrows():
                # Create rule
                rule_name = f"Atribuição automática - {row['Categoria']}"
                rule_id = rule_id_start
                rule_uuid = str(uuid.uuid4())
                
                rule_rows.append(f"({rule_id}, '{rule_name}', 'Regra criada automaticamente para atribuição de tickets', 'AND', 1, 'RuleTicket', {rule_id_start - 999}, '{rule_uuid}', 0, NOW(), NOW())")
                
                # Create criteria for category
                criteria_id = criteria_id_start
                criteria_rows.append(f"({criteria_id}, {rule_id}, 'itilcategories_id', 0, '{row['ID da Categoria']}')")
                
                # Create actions for SLA and Group assignment
                action_id_sla = action_id_start
                action_id_group = action_id_start + 1
                
                action_rows.append(f"({action_id_sla}, {rule_id}, 'assign', 'slas_id', '{row['ID do SLA']}')")
                action_rows.append(f"({action_id_group}, {rule_id}, 'assign', 'groups_id', '{row['ID do Grupo']}')")
                
                # Increment IDs
                rule_id_start += 1
                criteria_id_start += 1
                action_id_start += 2
            
            rules_section += ",\n".join(rule_rows) + ";\n"
            criteria_section += ",\n".join(criteria_rows) + ";\n"
            actions_section += ",\n".join(action_rows) + ";\n"
            
            section += rules_section + criteria_section + actions_section
            sql_parts.append(section)
            sql_sections['regras_atribuicao'] = section
    
    except Exception as e:
        logger.error(f"Error generating SQL: {str(e)}")
        raise
    
    # Combine all SQL parts
    sql_content = "".join(sql_parts)
    
    if return_sections:
        return sql_content, sql_sections
    else:
        return sql_content

if __name__ == '__main__':
    logger.info("Starting GLPI 10 SQL Generator application")
    logger.info(f"Server running on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', debug=True)
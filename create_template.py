import pandas as pd
import os

def create_excel_template(output_path):
    """
    Create a template Excel file with all required sheets and columns
    for the GLPI 10 SQL Generator.
    """
    # Create a Pandas Excel writer
    writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
    
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
    
    print(f"Template Excel file created at: {output_path}")
    print("This file contains all required sheets and columns for the GLPI 10 SQL Generator.")

if __name__ == "__main__":
    # Path for the output template file
    output_path = "c:\\Users\\5605723.HE\\Documents\\PROJETOS-VSA2024\\SISTEMAS\\APPs\\gerador_sql_glpi10\\glpi10_template.xlsx"
    
    create_excel_template(output_path)
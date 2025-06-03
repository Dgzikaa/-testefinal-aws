import requests
import hashlib
import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
import os
# import psycopg2  # Comentado - não usando banco de dados
import pyperclip
import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException

###########################
# CONFIGURAÇÕES COMUNS
###########################
# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Credenciais ContaHub
CONTAHUB_EMAIL = "digao@3768"
CONTAHUB_SENHA = "Geladeira@001"  # Senha pura

# Credenciais Google Sheets
GOOGLE_CREDENTIALS_PATH = "/home/ec2-user/google_credentials.json"
SHEET_NAME = "Base_de_dados_CA_ordinario"

# URL de login ContaHub
LOGIN_URL = "https://sp.contahub.com/rest/contahub.cmds.UsuarioCmd/login/17421701611337?emp=0"

# Database connection settings - COMENTADO (não usando banco de dados)
# RDS_HOST = "ordinariodb.cjkqcqimqh0e.us-east-2.rds.amazonaws.com"
# RDS_DB = "postgres"
# RDS_PORT = 5432
# RDS_USER = "digao3n"
# RDS_PASSWORD = "rodrigooliveira374"

###########################
# FUNÇÕES UTILITÁRIAS
###########################

def calculate_week_and_day(date_str):
    """Converte 'YYYY-MM-DD' em (dia_da_semana, numero_da_semana)."""
    try:
        # Remover aspas simples no início se existir
        if isinstance(date_str, str) and date_str.startswith("'"):
            date_str = date_str[1:]
            
        parsed_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        day_of_week = parsed_date.isoweekday()       # 1=Segunda, 7=Domingo
        week_number = parsed_date.isocalendar()[1]   # Número da semana no ano
        return day_of_week, week_number
    except ValueError:
        return "", ""

def format_monetary(value):
    """Formata valor monetário para duas casas decimais."""
    try:
        # Se for vazio ou None, retornar string vazia
        if value is None or value == "" or value == "None":
            return ""
            
        # Se for um dicionário ou lista, não é um valor monetário válido
        if isinstance(value, (dict, list)):
            return ""
            
        # Se já for um float, usar diretamente
        if isinstance(value, float):
            # Formatar com duas casas decimais usando vírgula como separador decimal
            return f"{value:.2f}".replace('.', ',')
            
        # Verificar se começa com aspas simples e remover
        if isinstance(value, str) and value.startswith("'"):
            value = value[1:]
            
        # Se começa com R$, remover para processamento
        if isinstance(value, str) and value.startswith("R$"):
            value = value[2:].strip()
            
        # Usar parse_float para converter para float
        value_float = parse_float(value)
        
        # Se o valor for zero, retornar string vazia
        if value_float == 0:
            return ""
            
        # Formatar com duas casas decimais usando vírgula como separador decimal
        return f"{value_float:.2f}".replace('.', ',')
    except Exception as e:
        print(f"[DEBUG] Erro ao formatar valor monetário '{value}': {str(e)}")
        # Em caso de erro, retornar string vazia
        return ""

def parse_float(value):
    """Parse a string to float, handling different number formats."""
    if value is None or value == "" or value == "None":
        return 0.0
        
    if isinstance(value, (int, float)):
        return float(value)
        
    # Convert to string
    value_str = str(value).strip()
    
    # Remove aspas simples no início
    if value_str.startswith("'"):
        value_str = value_str[1:]
    
    # Remove currency symbol
    value_str = value_str.replace('R$', '').strip()
    
    # If empty after removing currency symbol
    if not value_str:
        return 0.0
        
    # Handle Brazilian number format (1.234,56)
    if ',' in value_str and '.' in value_str:
        # Brazilian format with thousand separator
        value_str = value_str.replace('.', '').replace(',', '.')
    elif ',' in value_str:
        # Brazilian format without thousand separator
        value_str = value_str.replace(',', '.')
        
    try:
        return float(value_str)
    except (ValueError, TypeError):
        return 0.0

def get_date_range(days_back=1):
    """Retorna as datas de início e fim para a consulta."""
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days_back)
    
    return start_date.isoformat(), end_date.isoformat()

###########################
# FUNÇÕES PARA GOOGLE SHEETS
###########################

def update_columns_a_and_b(worksheet_name, date_column_index, new_data_start_row, new_data_end_row):
    """
    Atualiza colunas A e B com dia_da_semana e numero_da_semana, baseado na data na coluna especificada.
    """
    print("[DEBUG] Atualizando colunas A e B no Google Sheets...")
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=scope)
    gc = gspread.authorize(creds)

    sh = gc.open(SHEET_NAME)
    wks = sh.worksheet(worksheet_name)

    all_values = wks.get_all_values()
    
    # Verificar o número real de linhas
    actual_rows = len(all_values)
    if actual_rows <= 1:  # Somente cabeçalho ou vazio
        print("[INFO] Planilha vazia ou apenas com cabeçalho. Nada a fazer.")
        return
        
    # Ajustar o intervalo de linhas para não exceder o tamanho real da planilha
    new_data_start_row = min(new_data_start_row, actual_rows)
    new_data_end_row = min(new_data_end_row, actual_rows)
    
    print(f"[INFO] Atualizando colunas A e B para as linhas {new_data_start_row} até {new_data_end_row}")

    # Pegar apenas as colunas que nos interessam
    date_column_values = []
    try:
        # Converter coluna numérica para letra
        col_letter = ""
        if date_column_index < 26:
            col_letter = chr(65 + date_column_index)
        else:
            col_letter = f"A{chr(65 + date_column_index - 26)}"
            
        # Obter somente a coluna de data para evitar memória excessiva
        date_column_values = wks.get_values(f"{col_letter}:{col_letter}")
        print(f"[DEBUG] Obtidos {len(date_column_values)} valores da coluna {col_letter}")
    except Exception as e:
        print(f"[ERRO] Falha ao obter coluna de data: {e}")
        return

    # Função para limpar aspas simples
    def clean_quotes(value):
        if isinstance(value, str) and value.startswith("'"):
            return value[1:]
        return value

    updates = []
    for i in range(new_data_start_row - 1, new_data_end_row):
        try:
            if i < len(date_column_values) and date_column_values[i] and date_column_values[i][0]:
                date_value = date_column_values[i][0]
                
                # Remover aspas simples no início se existir
                date_value = clean_quotes(date_value)
                
                # Processar apenas se for uma data ISO8601 (YYYY-MM-DD...)
                if isinstance(date_value, str) and len(date_value) >= 10:
                    # Se a data está no formato "2025-03-16T00:00:00-0300"
                    # Extrair apenas a parte "2025-03-16"
                    if 'T' in date_value:
                        date_value = date_value.split('T')[0]
                    
                    # Calcular o dia da semana e semana do ano
                    day_of_week, week_number = calculate_week_and_day(date_value)
                    updates.append([day_of_week, week_number])
                    continue
            
            # Se não conseguir processar, manter os valores existentes
            if i < len(all_values) and len(all_values[i]) >= 2:
                updates.append([all_values[i][0], all_values[i][1]])
            else:
                updates.append([0, 0])  # Valores default
                
        except Exception as e:
            print(f"[ERRO] Falha ao processar linha {i+1}: {e}")
            # Manter os valores existentes em caso de erro
            if i < len(all_values) and len(all_values[i]) >= 2:
                updates.append([all_values[i][0], all_values[i][1]])
            else:
                updates.append([0, 0])  # Valores default

    try:
        # Atualizar as colunas A e B com os valores calculados
        wks.update(
            values=updates,
            range_name=f"A{new_data_start_row}:B{new_data_end_row}",
            value_input_option="RAW"  # Usar RAW em vez de USER_ENTERED para evitar formatação automática
        )
        print("[INFO] Colunas A e B atualizadas com sucesso!")
    except Exception as e:
        print(f"[ERRO] Falha ao atualizar as colunas A e B: {e}")
        time.sleep(10)
        # Tenta novamente
        update_columns_a_and_b(worksheet_name, date_column_index, new_data_start_row, new_data_end_row)

def append_to_google_sheets(worksheet_name, data, start_column="A"):
    """
    Recebe 'data' como lista de listas (linhas/colunas) e insere na planilha,
    começando na coluna especificada, pulando a primeira linha (cabeçalho).
    
    Args:
        worksheet_name: Nome da planilha
        data: Lista de listas com os dados a serem inseridos
        start_column: Coluna inicial para inserção (default: "A")
    """
    print("[DEBUG] Conectando ao Google Sheets...")
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=scope)
    gc = gspread.authorize(creds)

    sh = gc.open(SHEET_NAME)
    wks = sh.worksheet(worksheet_name)

    # Verifica quantidade de linhas/colunas atuais
    all_values = wks.get_all_values()
    num_rows = len(all_values)
    num_cols = len(all_values[0]) if num_rows > 0 else 0
    total_cells = num_rows * num_cols

    MAX_CELLS = 10_000_000
    MAX_SAFE_ROWS = 800_000

    print(f"[INFO] Células atuais usadas: {total_cells} / {MAX_CELLS}")
    if total_cells > MAX_CELLS * 0.95 or num_rows >= MAX_SAFE_ROWS:
        print(f"[ALERTA] Limite de células atingido! Dados NÃO serão adicionados.")
        return

    if not data:
        print("[INFO] Nenhum dado para inserir no Google Sheets.")
        return

    # CONFIGURAÇÃO ESPECÍFICA PARA CADA PLANILHA
    # Definir índices das colunas que precisam de tratamento especial
    date_indices = []
    monetary_indices = []
    
    # Para a planilha CH_PeriodoPP
    if worksheet_name == "CH_PeriodoPP":
        date_indices = [4, 17, 18, 22, 23]  # dt_gerencial, dt_contabil, ultimo_pedido, nf_dtcontabil, vd_dtcontabil
        monetary_indices = [11, 12, 13, 14, 15]  # vr_pagamentos, vr_produtos, vr_repique, vr_couvert, vr_desconto
    elif worksheet_name == "CH_AnaliticoPP":
        date_indices = [13]  # vd_dtgerencial
        monetary_indices = [19, 20, 21, 22]  # qtd, desconto, valorfinal, custo
    elif worksheet_name == "CH_NFs":
        date_indices = [3, 4]  # vd_dtgerencial, nf_dtcontabil
        monetary_indices = [12, 13, 14, 15, 16, 17, 18]  # diversos valores monetários
    elif worksheet_name == "CH_Tempo":
        date_indices = [30]  # dia
        monetary_indices = [11, 12, 13, 14, 15, 16, 34]  # diversos valores numéricos
    elif worksheet_name == "CH_Pagamentos":
        date_indices = [4, 5, 9]  # dt_gerencial, dt_contabil, pgtdataincl
        monetary_indices = [13]  # valor
    
    # Funções auxiliares para processamento
    def clean_string(value):
        """Remove aspas e espaços extras de strings"""
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if cleaned.startswith("'"):
            cleaned = cleaned[1:]
        return cleaned
    
    def convert_date(value):
        """
        Limpa e formata uma string de data para ser reconhecida pelo Google Sheets.
        Apenas remove aspas e formata corretamente, sem transformar em fórmula.
        """
        if not value:
            return ""
            
        # Se já for um objeto datetime, converter para string no formato YYYY-MM-DD
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.strftime("%Y-%m-%d")
            
        # Se for string, processar
        if isinstance(value, str):
            # Limpar aspas e espaços
            value = clean_string(value)
            
            # Se vazio após limpeza
            if not value or value.lower() == "null":
                return ""
                
            # Se tiver T, extrair apenas a parte da data
            if "T" in value:
                value = value.split("T")[0]
                
            # Verificar se é uma data no formato YYYY-MM-DD
            if len(value) >= 10 and value[4] == "-" and value[7] == "-":
                try:
                    # Apenas validar se é uma data correta, sem converter para fórmula
                    datetime.datetime.strptime(value, "%Y-%m-%d")
                    return value  # Retorna a data limpa no formato YYYY-MM-DD
                except ValueError:
                    # Se falhar na conversão, retornar como está
                    return value
                    
        return value
    
    def convert_number(value):
        """Converte um valor para número formatado para o Google Sheets"""
        if value is None or value == "":
            return ""  # Vazio em vez de 0 para células vazias
            
        # Se já for número, manter
        if isinstance(value, (int, float)):
            # Retornar diretamente o valor numérico sem formatação
            return value
            
        # Se for string, processar
        if isinstance(value, str):
            # Limpar aspas e espaços
            value = clean_string(value)
            
            # Se vazio após limpeza
            if not value or value.lower() == "null":
                return ""
                
            # Remover R$ se presente
            if value.startswith("R$"):
                value = value.replace("R$", "").strip()
                
            # Converter formato de número brasileiro
            try:
                if "," in value:
                    if "." in value:  # 1.234,56 -> 1234.56
                        value = value.replace(".", "").replace(",", ".")
                    else:  # 1234,56 -> 1234.56
                        value = value.replace(",", ".")
                        
                # Tentar converter para float
                if value.replace(".", "", 1).isdigit():
                    return float(value)
                else:
                    return value  # Manter como está se não for possível converter
            except:
                return value  # Manter como está em caso de erro
                
        return value
    
    # Processar dados para garantir tipos corretos
    processed_data = []
    
    for row in data:
        processed_row = []
        
        for i, cell in enumerate(row):
            # Processar valores de acordo com o tipo de coluna
            if i in date_indices:
                processed_cell = convert_date(cell)
            elif i in monetary_indices:
                processed_cell = convert_number(cell)
            else:
                # Para outras colunas, apenas limpar strings
                if isinstance(cell, str):
                    processed_cell = clean_string(cell)
                else:
                    processed_cell = cell
                    
            processed_row.append(processed_cell)
            
        processed_data.append(processed_row)
    
    # Debug - mostrar o primeiro registro
    if processed_data:
        print("[DEBUG] Primeiro registro processado (exemplos):")
        for j, val in enumerate(processed_data[0][:min(5, len(processed_data[0]))]):  # Mostra apenas primeiros 5 valores
            print(f"  Coluna {j+1}: {val} (tipo: {type(val).__name__})")
        
        # Mostra também algumas colunas de datas e valores se existirem
        for idx in date_indices[:2]:  # Mostra até 2 exemplos de colunas de data
            if idx < len(processed_data[0]):
                print(f"  Coluna de data {idx+1}: {processed_data[0][idx]}")
        
        for idx in monetary_indices[:2]:  # Mostra até 2 exemplos de colunas monetárias
            if idx < len(processed_data[0]):
                print(f"  Coluna monetária {idx+1}: {processed_data[0][idx]}")
    
    # Sempre começa da linha 2 para preservar o cabeçalho
    first_empty_row = max(2, num_rows + 1)
    last_row = first_empty_row + len(processed_data) - 1

    # Se ultrapassar o limite seguro de linhas
    if last_row >= MAX_SAFE_ROWS:
        print(f"[ALERTA] O limite de linhas está sendo atingido. Reduzindo dados adicionados...")
        processed_data = processed_data[:MAX_SAFE_ROWS - first_empty_row]
        last_row = MAX_SAFE_ROWS

    try:
        # Inserir dados na planilha
        wks.update(
            values=processed_data,
            range_name=f"{start_column}{first_empty_row}",
            value_input_option="USER_ENTERED"  # Usar USER_ENTERED para interpretar fórmulas
        )
        print("[INFO] Dados adicionados ao Google Sheets com sucesso!")
        return first_empty_row, last_row
    except Exception as e:
        print(f"[ERRO] Falha ao adicionar dados no Google Sheets: {e}")
        time.sleep(5)
        
        # Tentar método alternativo em lotes menores
        try:
            print("[INFO] Tentando método alternativo com lotes menores...")
            batch_size = 500
            current_row = first_empty_row
            
            for i in range(0, len(processed_data), batch_size):
                batch = processed_data[i:i+batch_size]
                if batch:
                    wks.update(
                        values=batch,
                        range_name=f"{start_column}{current_row}",
                        value_input_option="USER_ENTERED"  # Usar USER_ENTERED para interpretar fórmulas
                    )
                    current_row += len(batch)
                    print(f"[INFO] Inserido lote de {len(batch)} registros")
                    time.sleep(2)
            
            print("[INFO] Dados adicionados com sucesso (método alternativo)!")
            return first_empty_row, last_row
        except Exception as e2:
            print(f"[ERRO] Falha no método alternativo: {e2}")
            return None

def remove_duplicates(worksheet_name):
    """
    Remove registros duplicados da planilha híbrida correspondente.
    Mapeia automaticamente a worksheet para a planilha híbrida correta.
    """
    print(f"[INFO] Removendo duplicatas da aba {worksheet_name} (sistema híbrido)...")
    
    # Verificar se a worksheet está mapeada para uma planilha híbrida
    if worksheet_name not in WORKSHEET_TO_SHEET:
        print(f"[ERRO] Aba {worksheet_name} não está mapeada para planilha híbrida!")
        print(f"[INFO] Abas mapeadas: {list(WORKSHEET_TO_SHEET.keys())}")
        return 0
    
    sheet_id = WORKSHEET_TO_SHEET[worksheet_name]
    print(f"[INFO] Usando planilha híbrida: {sheet_id}")
    
    # Conectar ao Google Sheets
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=scope)
    gc = gspread.authorize(creds)

    # Abrir a planilha híbrida correta
    try:
        sh = gc.open_by_key(sheet_id)
        print(f"[INFO] Planilha híbrida aberta: {sh.title}")
    except Exception as e:
        print(f"[ERRO] Falha ao abrir planilha híbrida {sheet_id}: {e}")
        return 0
    
    # Abrir a aba específica
    try:
        wks = sh.worksheet(worksheet_name)
        print(f"[INFO] Aba encontrada: {worksheet_name}")
    except Exception as e:
        print(f"[ERRO] Aba {worksheet_name} não encontrada na planilha híbrida: {e}")
        return 0
    
    # Obter todos os dados, incluindo o cabeçalho
    data = wks.get_all_values()
    
    if not data or len(data) <= 1:
        print("[INFO] Planilha vazia ou apenas com cabeçalho. Nada a fazer.")
        return 0
    
    # Separar cabeçalho e dados
    header = data[0]
    rows = data[1:]
    
    print(f"[INFO] Total de registros antes da deduplicação: {len(rows)}")
    
    # Configurar índices para formatação especial
    if worksheet_name == "CH_Tempo":
        date_indices = [30]    # AE (dia)
        monetary_indices = [11, 12, 13, 14, 15, 16, 34]  # diversos valores
    elif worksheet_name == "CH_NFs":
        date_indices = [3, 4]  # D, E (vd_dtgerencial, nf_dtcontabil)
        monetary_indices = [12, 13, 14, 15, 16, 17, 18]  # diversos valores
    elif worksheet_name == "CH_AnaliticoPP":
        date_indices = [13]  # N (vd_dtgerencial)
        monetary_indices = [19, 20, 21, 22]  # diversos valores
    elif worksheet_name == "CH_PeriodoPP":
        date_indices = [4, 17, 18, 22, 23]  # E, R, S, W, X (dt_gerencial, dt_contabil, etc.)
        monetary_indices = [11, 12, 13, 14, 15]  # diversos valores
    elif worksheet_name == "CH_Pagamentos":
        date_indices = [4, 5, 9]  # E, F, J (dt_gerencial, dt_contabil, pgtdataincl)
        monetary_indices = [13]  # N (valor)
    elif worksheet_name == "CH_FatporHora":
        date_indices = [2]  # C (vd_dtgerencial)
        monetary_indices = [7]  # H (valor)
    elif worksheet_name == "CA_VisaoCompetencia":
        date_indices = []  # Configurar conforme necessário
        monetary_indices = []  # Configurar conforme necessário
    else:
        date_indices = []
        monetary_indices = []

    # Usar todas as colunas para comparação de duplicatas
    key_indexes = list(range(len(header)))
    
    # Função auxiliar para limpar aspas de uma string
    def clean_quotes(value):
        if isinstance(value, str) and value.startswith("'"):
            return value[1:]
        return value
    
    # Função para detectar e formatar datas
    def format_date(value):
        """
        Limpa e formata uma string de data para ser reconhecida pelo Google Sheets.
        """
        if not isinstance(value, str):
            return value
            
        # Remover aspas simples
        value = clean_quotes(value)
        
        # Verificar se é uma data no formato YYYY-MM-DD ou YYYY-MM-DDT...
        if len(value) >= 10 and (
            (value[4] == '-' and value[7] == '-') or
            ('T' in value and value[:10].replace('-', '').isdigit())
        ):
            # Se contiver 'T', pegar apenas a parte da data
            if 'T' in value:
                value = value.split('T')[0]
                
            # Verificar se é uma data válida
            try:
                datetime.datetime.strptime(value, '%Y-%m-%d')
                return value
            except:
                pass
        return value
    
    # Função para detectar e formatar valores numéricos/monetários
    def format_value(value):
        if not isinstance(value, str):
            return value
            
        # Remover aspas simples
        value = clean_quotes(value)
        
        # Se começar com R$, é um valor monetário
        if value.startswith('R$'):
            try:
                # Tentar converter para número
                num_value = parse_float(value)
                return num_value
            except:
                return value
            
        # Verificar se é um número
        try:
            # Se tiver vírgula como separador decimal, converter
            if ',' in value:
                if '.' in value:  # Formato brasileiro com separador de milhar
                    numeric_value = float(value.replace('.', '').replace(',', '.'))
                else:  # Apenas vírgula como separador decimal
                    numeric_value = float(value.replace(',', '.'))
                return numeric_value
            # Verificar se é um número sem formatação
            return float(value) if value.replace('.', '', 1).isdigit() else value
        except:
            return value
    
    # Limpar aspas e coletar registros únicos
    unique_rows = {}
    
    for row in rows:
        # Limpar aspas simples e formatar todos os valores da linha
        clean_row = []
        for i, cell in enumerate(row):
            # Primeiro limpar aspas
            clean_value = clean_quotes(cell)
            
            # Aplicar formatação específica baseada no tipo de coluna
            if i in date_indices:
                final_value = format_date(clean_value)
            elif i in monetary_indices:
                final_value = format_value(clean_value)
                # Converter zeros para campos vazios (manter consistência com sistema)
                if str(final_value) == "0" or str(final_value) == "0.0":
                    final_value = ""
            else:
                final_value = clean_value
                
            clean_row.append(final_value)
        
        # Criar chave única baseada nas colunas-chave
        key_parts = []
        for idx in key_indexes:
            if idx < len(clean_row):
                # Garantir que a chave não tenha aspas simples ou fórmulas
                value = str(clean_row[idx])
                if isinstance(value, str):
                    if value.startswith("'"):
                        value = value[1:]
                    elif value.startswith("=DATA("):
                        # Extrair a data da fórmula para a chave
                        try:
                            # Extrair ano, mês, dia
                            date_parts = value.replace("=DATA(", "").replace(")", "").split(";")
                            if len(date_parts) == 3:
                                value = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"
                        except:
                            pass
                
                # Normalizar valores vazios e zeros para comparação
                if value == "" or value == "0" or value == "0.0":
                    if idx in monetary_indices:  # Se for coluna monetária, normalizar como vazio
                        value = ""
                
                key_parts.append(value)
            else:
                key_parts.append("")
        
        key = "|".join(key_parts)
        unique_rows[key] = clean_row
    
    # Obter lista de registros únicos
    unique_data = list(unique_rows.values())
    
    duplicates_removed = len(rows) - len(unique_data)
    print(f"[INFO] Registros após deduplicação: {len(unique_data)}")
    print(f"[INFO] Duplicatas removidas: {duplicates_removed}")
    
    # Se não há duplicatas, não é necessário atualizar a planilha
    if duplicates_removed == 0:
        print("[INFO] Não foram encontradas duplicatas. Nenhuma alteração necessária.")
        return 0
    
    # Limpar planilha mantendo apenas o cabeçalho
    try:
        print("[INFO] Limpando planilha e preparando para inserir dados deduplcados...")
        
        # Limpar o conteúdo da planilha e adicionar header + dados únicos
        wks.clear() 
        time.sleep(2)
        
        # Primeiro inserir o cabeçalho
        wks.update('A1', [header], value_input_option='RAW')
        time.sleep(1)
        
        # Depois inserir os dados únicos
        if unique_data:
            wks.update('A2', unique_data, value_input_option='USER_ENTERED')
            
        print(f"[INFO] ✅ Deduplicação concluída: {duplicates_removed} duplicatas removidas!")
        return duplicates_removed
        
    except Exception as e:
        print(f"[ERRO] Falha ao atualizar planilha: {e}")
        return 0

def log_info(message):
    """Registra mensagens de informação."""
    print(f"[INFO] {message}")

###########################
# FUNÇÕES PARA DATABASE
###########################

# def connect_to_database():
#     """Conecta ao banco de dados PostgreSQL."""
#     try:
#         print(f"[INFO] Conectando ao PostgreSQL em {RDS_HOST}...")
#         conn = psycopg2.connect(
#             host=RDS_HOST,
#             database=RDS_DB,
#             user=RDS_USER,
#             password=RDS_PASSWORD,
#             port=RDS_PORT
#         )
#         # Ativar autocommit para evitar problemas com set_session
#         conn.autocommit = True
#         print("[INFO] Conexão com o PostgreSQL estabelecida com sucesso!")
#         return conn
#     except Exception as e:
#         print(f"[ERRO] Falha ao conectar ao PostgreSQL: {str(e)}")
#         return None

# Função connect_to_database comentada - não usando banco de dados
def connect_to_database():
    """Função desabilitada - não usando banco de dados."""
    print("[INFO] Conexão com banco de dados ignorada - banco desabilitado.")
    return None

# def create_table_if_not_exists(conn, table_name, table_schema):
#     """
#     Cria a tabela no PostgreSQL se ela não existir.
#     
#     Args:
#         conn: Conexão com o banco de dados
#         table_name: Nome da tabela
#         table_schema: Schema SQL para criação da tabela
#     """
#     try:
#         cursor = conn.cursor()
#         cursor.execute(table_schema)
#         # commit não é necessário com autocommit=True
#         print(f"[INFO] Tabela {table_name} verificada/criada com sucesso!")
#     except Exception as e:
#         print(f"[ERRO] Falha ao criar tabela {table_name}: {str(e)}")
#         # rollback não é necessário com autocommit=True

# Função create_table_if_not_exists comentada - não usando banco de dados  
def create_table_if_not_exists(conn, table_name, table_schema):
    """Função desabilitada - não usando banco de dados."""
    print(f"[INFO] Criação de tabela {table_name} ignorada - banco desabilitado.")
    return True

# def remove_database_duplicates(conn, table_name, unique_columns):
#     """
#     Remove duplicatas na tabela do PostgreSQL.
#     
#     Args:
#         conn: Conexão com o banco de dados
#         table_name: Nome da tabela
#         unique_columns: Lista de colunas que definem um registro único
#     """
#     print(f"[INFO] Removendo duplicatas na tabela {table_name}...")
#     try:
#         cursor = conn.cursor()
#         
#         # Verificar se as colunas necessárias existem
#         cursor.execute(f"""
#         SELECT column_name 
#         FROM information_schema.columns 
#         WHERE table_name = '{table_name}'
#         AND column_name IN ({', '.join([f"'{col}'" for col in unique_columns])});
#         """)
#         
#         existing_columns = [row[0] for row in cursor.fetchall()]
#         
#         if not existing_columns:
#             print(f"[ALERTA] Não foi possível remover duplicatas: nenhuma das colunas necessárias existe na tabela {table_name}.")
#             return
#             
#         # Usar apenas as colunas que existem na tabela para a verificação de duplicatas
#         valid_columns = [col for col in unique_columns if col in existing_columns]
#         
#         if not valid_columns:
#             print(f"[ALERTA] Não foi possível remover duplicatas: colunas necessárias não existem na tabela {table_name}.")
#             return
#             
#         # Construir a condição WHERE para identificar duplicatas usando apenas as colunas válidas
#         where_condition = " AND ".join([f"a.{col} = b.{col}" for col in valid_columns])
#         
#         # Remover registros duplicados mantendo apenas o primeiro (menor ctid)
#         query = f"""
#         DELETE FROM {table_name} a
#         WHERE EXISTS (
#             SELECT 1 FROM {table_name} b
#             WHERE {where_condition}
#             AND a.ctid > b.ctid
#         );
#         """
#         
#         cursor.execute(query)
#         deleted_count = cursor.rowcount
#         conn.commit()
#         print(f"[INFO] {deleted_count} duplicatas removidas da tabela {table_name} com sucesso!")
#     except Exception as e:
#         print(f"[ERRO] Falha ao remover duplicatas da tabela {table_name}: {str(e)}")
#         conn.rollback()

# Função remove_database_duplicates comentada - não usando banco de dados
def remove_database_duplicates(conn, table_name, unique_columns):
    """Função desabilitada - não usando banco de dados."""
    print(f"[INFO] Remoção de duplicatas da tabela {table_name} ignorada - banco desabilitado.")
    return True

###########################
# FUNÇÕES PARA CONTAHUB API
###########################

def login_contahub():
    """Realiza login no ContaHub e retorna a sessão."""
    print("[INFO] Realizando login no ContaHub...")
    
    try:
        # Criar sessão
        session = requests.Session()
        
        # Preparar dados de login - usando os parâmetros corretos
        login_data = {
            "usr_email": CONTAHUB_EMAIL,
            "usr_password_sha1": hashlib.sha1(CONTAHUB_SENHA.encode()).hexdigest()
        }
        
        # Configurar headers
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        })
        
        # Fazer requisição de login com data (não json)
        response = session.post(LOGIN_URL, data=login_data)
        
        # Salvar resposta para debug
        with open(os.path.join(SCRIPT_DIR, "login_response.json"), "w", encoding="utf-8") as f:
            f.write(response.text)
            
        # Verificar status da resposta
        if response.status_code != 200:
            print(f"[ERRO] Falha no login. Status: {response.status_code}")
            print(f"[DEBUG] Resposta: {response.text[:500]}...")
            return None
            
        # Verificar se a resposta contém erro
        if "error" in response.text.lower() or "invalid" in response.text.lower():
            print(f"[ERRO] Login rejeitado: {response.text[:200]}")
            return None
            
        print(f"[INFO] Login realizado com sucesso para {CONTAHUB_EMAIL}")
        return session
            
    except requests.exceptions.RequestException as e:
        print(f"[ERRO] Erro na requisição de login: {str(e)}")
        return None
    except Exception as e:
        print(f"[ERRO] Erro inesperado no login: {str(e)}")
        return None

def fetch_data_api(session, query_url):
    """
    Busca dados do ContaHub usando a API.
    
    Args:
        session: Sessão autenticada
        query_url: URL completa da consulta
    """
    print(f"[INFO] Buscando dados da API ContaHub...")
    
    try:
        response = session.get(query_url)
        
        # Salvar a resposta para debug
        with open(os.path.join(SCRIPT_DIR, "query_response.json"), "w", encoding="utf-8") as f:
            f.write(response.text)
            
        if response.status_code != 200:
            print(f"[ERRO] Falha ao buscar dados. Status: {response.status_code}")
            print(f"[DEBUG] Resposta: {response.text[:500]}...")
            return None
            
        data = response.json()
        
        # Verificar se a resposta contém a chave 'list'
        if 'list' not in data or not data['list']:
            print("[ALERTA] Nenhum registro encontrado para o período.")
            return []
            
        records = data['list']
        print(f"[INFO] Total de registros encontrados: {len(records)}")
        return records
        
    except Exception as e:
        print(f"[ERRO] Falha ao buscar ou processar dados: {str(e)}")
        return None

###########################
# FUNÇÕES PARA SELENIUM (CONTAHUB WEB)
###########################

def init_selenium_driver():
    """Inicializa o driver do Selenium para Edge."""
    print("[DEBUG] Iniciando Edge WebDriver com Selenium Manager...")
    edge_options = webdriver.EdgeOptions()
    driver = webdriver.Edge(options=edge_options)
    wait = WebDriverWait(driver, 20)
    return driver, wait

def login_contahub_selenium(driver, wait):
    """Realiza login no ContaHub via Selenium."""
    print("[DEBUG] Acessando página de Login do ContaHub...")
    driver.get("https://sp.contahub.com/")

    print("[DEBUG] Preenchendo E-mail e Senha...")
    email_input = wait.until(EC.presence_of_element_located((By.ID, "loginEmail")))
    email_input.send_keys(CONTAHUB_EMAIL)
    time.sleep(1)

    password_input = wait.until(EC.presence_of_element_located((By.ID, "loginPass")))
    password_input.send_keys(CONTAHUB_SENHA)
    time.sleep(1)

    login_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[7]/center/div/form/div[4]/input"))
    )
    login_button.click()
    time.sleep(2)
    
    print("[INFO] Login realizado com sucesso!")

def fetch_data_selenium(driver, wait, start_date, end_date, ok_button_xpath, export_button_xpath):
    """
    Busca dados do ContaHub usando Selenium.
    
    Args:
        driver: Driver do Selenium
        wait: Objeto WebDriverWait
        start_date: Data inicial no formato YYYY-MM-DD
        end_date: Data final no formato YYYY-MM-DD
        ok_button_xpath: XPath do botão OK para gerar o relatório
        export_button_xpath: XPath do botão de exportação
    """
    print(f"[DEBUG] Configurando filtros de data: {start_date} até {end_date}...")

    start_date_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[7]/div[1]/div[1]/input[1]"))
    )
    driver.execute_script(f"arguments[0].value = '{start_date}';", start_date_input)
    time.sleep(1)

    end_date_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[7]/div[1]/div[1]/input[2]"))
    )
    driver.execute_script(f"arguments[0].value = '{end_date}';", end_date_input)
    time.sleep(1)

    print("[DEBUG] Clicando em 'OK' para gerar relatório...")
    ok_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, ok_button_xpath))
    )
    ok_button.click()
    time.sleep(2)

    # Tratamento de alerta inesperado
    try:
        WebDriverWait(driver, 5).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        print(f"[ALERTA] Alerta detectado: {alert.text}")
        alert.dismiss()
        print("[INFO] Alerta fechado com sucesso.")
        return []
    except UnexpectedAlertPresentException as e:
        print(f"[ERRO] Alerta inesperado: {e}")
        return []
    except:
        print("[DEBUG] Nenhum alerta encontrado, continuando...")

    print("[DEBUG] Clicando no ícone de exportar para Excel...")
    export_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, export_button_xpath))
    )
    export_button.click()
    time.sleep(5)

    print("[DEBUG] Extraindo dados do modal...")
    modal_textarea = wait.until(EC.presence_of_element_located((By.ID, "cpaste")))
    modal_textarea.click()
    time.sleep(1)

    pyautogui.hotkey('ctrl', 'a')
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(1)

    report_data = pyperclip.paste().strip()
    if not report_data:
        raise ValueError("[ERRO] Nenhum dado foi copiado do relatório. Verifique o modal e tente novamente.")

    # Fecha o modal
    try:
        modal = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[11]/div/textarea")))
        modal.click()
        time.sleep(1)
        pyautogui.press('esc')
    except Exception as e:
        print(f"[ALERTA] Não foi possível fechar o modal: {e}")

    parsed_data = [line.split('\t') for line in report_data.splitlines()]
    print("[DEBUG] Dados extraídos com sucesso!")
    return parsed_data

# Configurações específicas para cada script
SCRIPT_CONFIGS = {
    'analitico': {
        'worksheet_name': 'CH_AnaliticoPP',
        'date_column_index': 13,
        'query_base_url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1742237860621',
        'table_name': 'contahub_analitico',
        'table_schema': """
        CREATE TABLE IF NOT EXISTS contahub_analitico (
            id SERIAL PRIMARY KEY,
            dia_semana INTEGER,
            semana INTEGER,
            vd VARCHAR(50),
            vd_mesadesc VARCHAR(100),
            vd_localizacao VARCHAR(100),
            itm VARCHAR(50),
            trn VARCHAR(50),
            trn_desc VARCHAR(100),
            prefixo VARCHAR(50),
            tipo VARCHAR(50),
            tipovenda VARCHAR(50),
            ano VARCHAR(4),
            mes VARCHAR(10),
            vd_dtgerencial DATE,
            usr_lancou VARCHAR(100),
            prd VARCHAR(50),
            prd_desc VARCHAR(255),
            grp_desc VARCHAR(100),
            loc_desc VARCHAR(100),
            qtd NUMERIC(10, 2),
            desconto NUMERIC(10, 2),
            valorfinal NUMERIC(10, 2),
            custo NUMERIC(10, 2),
            itm_obs TEXT,
            comandaorigem VARCHAR(50),
            itemorigem VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        'unique_columns': ['vd', 'itm', 'prd']
    },
    'pagamentos': {
        'worksheet_name': 'CH_Pagamentos',
        'date_column_index': 4,
        'query_base_url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1742174377035',
        'table_name': 'contahub_pagamentos',
        'table_schema': """
        CREATE TABLE IF NOT EXISTS contahub_pagamentos (
            id SERIAL PRIMARY KEY,
            dia_semana INTEGER,
            semana INTEGER,
            vd VARCHAR(50),
            trn VARCHAR(50),
            dt_gerencial DATE,
            dt_contabil DATE,
            vd_mesadesc VARCHAR(100),
            vd_localizacao VARCHAR(100),
            pgt VARCHAR(50),
            pgtdataincl DATE,
            pgthorainc VARCHAR(50),
            tpg VARCHAR(50),
            tpg_descricao VARCHAR(100),
            valor NUMERIC(10, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        'unique_columns': ['vd', 'pgt', 'tpg', 'valor']
    },
    'periodo': {
        'worksheet_name': 'CH_PeriodoPP',
        'date_column_index': 4,  # Índice da coluna E (dt_gerencial)
        'query_base_url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1742232159394',
        'table_name': 'contahub_periodo',
        'table_schema': """
        CREATE TABLE IF NOT EXISTS contahub_periodo (
            vd VARCHAR(50),
            dia_semana INTEGER,
            semana INTEGER,
            trn VARCHAR(50),
            dt_gerencial DATE,
            tipovenda VARCHAR(50),
            vd_mesadesc VARCHAR(50),
            vd_localizacao VARCHAR(100),
            usr_abriu VARCHAR(100),
            pessoas INTEGER,
            qtd_itens INTEGER,
            vr_pagamentos NUMERIC(10, 2),
            vr_produtos NUMERIC(10, 2),
            vr_repique NUMERIC(10, 2),
            vr_couvert NUMERIC(10, 2),
            vr_desconto NUMERIC(10, 2),
            motivo VARCHAR(255),
            dt_contabil DATE,
            ultimo_pedido TIMESTAMP,
            vd_cpf VARCHAR(20),
            nf_autorizada VARCHAR(5),
            nf_chaveacesso VARCHAR(255),
            nf_dtcontabil VARCHAR(50),
            vd_dtcontabil DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (vd, dt_gerencial)
        );
        """,
        'unique_columns': ['vd', 'dt_gerencial']
    },
    'tempo': {
        'worksheet_name': 'CH_Tempo',
        'date_column_index': 30,  # Índice da coluna AE (dia)
        'query_base_url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery',
        'table_name': 'contahub_tempo',
        'unique_columns': ['vd', 'itm'],
        'table_schema': """
        CREATE TABLE IF NOT EXISTS contahub_tempo (
            id SERIAL PRIMARY KEY,
            dia_semana INTEGER,
            semana INTEGER,
            grp_desc VARCHAR(100),
            prd_desc VARCHAR(255),
            vd VARCHAR(50),
            itm VARCHAR(50),
            t0_lancamento VARCHAR(100),
            t1_prodini VARCHAR(100),
            t2_prodfim VARCHAR(100),
            t3_entrega VARCHAR(100),
            t0_t1 NUMERIC(10, 2) NULL,
            t0_t2 NUMERIC(10, 2) NULL,
            t0_t3 NUMERIC(10, 2) NULL,
            t1_t2 NUMERIC(10, 2) NULL,
            t1_t3 NUMERIC(10, 2) NULL,
            t2_t3 NUMERIC(10, 2) NULL,
            prd VARCHAR(50),
            prd_idexterno VARCHAR(50),
            loc_desc VARCHAR(100),
            vd_mesadesc VARCHAR(100),
            vd_localizacao VARCHAR(100),
            usr_abriu VARCHAR(100),
            usr_lancou VARCHAR(100),
            usr_produziu VARCHAR(100),
            usr_entregou VARCHAR(100),
            usr_transfcancelou VARCHAR(100),
            prefixo VARCHAR(50),
            tipovenda VARCHAR(50),
            ano VARCHAR(4),
            mes VARCHAR(10),
            dia VARCHAR(100),
            dds VARCHAR(20),
            diadasemana VARCHAR(20),
            hora VARCHAR(10),
            itm_qtd NUMERIC(10, 2) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    },
    'nf': {
        'worksheet_name': 'CH_NFs',
        'date_column_index': 3,  # Índice da coluna D (vd_dtgerencial)
        'query_base_url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1742268006590',
        'table_name': 'contahub_nfs',
        'unique_columns': ['cnpj', 'vd_dtgerencial', 'nf_serie', 'valor_autorizado'],
        'table_schema': """
        CREATE TABLE IF NOT EXISTS contahub_nfs (
            id SERIAL PRIMARY KEY,
            dia_semana INTEGER,
            semana INTEGER,
            cnpj VARCHAR(20),
            vd_dtgerencial DATE,
            nf_dtcontabil DATE,
            nf_tipo VARCHAR(50),
            nf_ambiente VARCHAR(50),
            nf_serie VARCHAR(10),
            subst_nfe_nfce VARCHAR(5),
            cancelada VARCHAR(5),
            autorizada VARCHAR(5),
            inutilizada VARCHAR(5),
            valor_autorizado NUMERIC(10, 2),
            valor_substituido_nfe_nfce NUMERIC(10, 2),
            valor_a_apurar NUMERIC(10, 2),
            vrst_autorizado NUMERIC(10, 2),
            vrisento_autorizado NUMERIC(10, 2),
            valor_cancelado NUMERIC(10, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    },
    'fatporhora': {
        'worksheet_name': 'CH_FatporHora',
        'date_column_index': 2,  # Índice da coluna C (vd_dtgerencial)
        'query_base_url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1745334526910',
        'table_name': 'contahub_fatporhora',
        'unique_columns': ['vd_dtgerencial', 'hora'],
        'table_schema': """
        CREATE TABLE IF NOT EXISTS contahub_fatporhora (
            id SERIAL PRIMARY KEY,
            dia_semana INTEGER,
            semana INTEGER,
            vd_dtgerencial DATE,
            dds VARCHAR(3),
            dia VARCHAR(20),
            hora VARCHAR(10),
            qtd INTEGER,
            valor NUMERIC(10, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (vd_dtgerencial, hora)
        );
        """
    }
} 

# PLANILHAS HÍBRIDAS - NOVA CONFIGURAÇÃO
HYBRID_SHEETS = {
    "vendas": {
        "id": "1eI11IWdwUce_2P27eKoltMT19D4Dvgv6wb7T8HNv6DY",
        "name": "Vendas_ordinario",
        "modules": ["CH_AnaliticoPP", "CH_Pagamentos", "CH_FatporHora"]
    },
    "fiscal": {
        "id": "1Dk4mOHfx5FsxTVhsqnYF-todecmUVvbOqaF69s14YTY", 
        "name": "Fiscal_ordinario",
        "modules": ["CH_NFs", "CH_PeriodoPP"]
    },
    "operacional": {
        "id": "1FZPQtQXN_To5qgJVHYu7o55A0TXRf8hj7UABUTsMrTY",
        "name": "Operacional_ordinario", 
        "modules": ["CH_Tempo", "CA_VisaoCompetencia"]
    }
}

# Mapeamento de módulos para planilhas híbridas
WORKSHEET_TO_SHEET = {}
for sheet_key, sheet_info in HYBRID_SHEETS.items():
    for module in sheet_info["modules"]:
        WORKSHEET_TO_SHEET[module] = sheet_info["id"] 
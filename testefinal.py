#!/usr/bin/env python3
"""
TesteFinal AWS PRODUÇÃO - Script completo para execução diária na AWS
Baseado no testefinal.py original mas otimizado para AWS EC2
VERSÃO HÍBRIDA - Usa 3 planilhas especializadas + Visão de Competência
"""
import requests
import json
import logging
import hashlib
from datetime import datetime, timedelta
import boto3
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
import sys
import argparse
import re
import math
import time
import pyotp

# Configurar logging ANTES de outros imports que podem usar logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Selenium imports para Visão de Competência
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("⚠️ Selenium não disponível - módulo Visão de Competência desabilitado")

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback para Python < 3.9
    try:
        import pytz
        ZoneInfo = None
    except ImportError:
        ZoneInfo = None
        pytz = None

try:
    import numpy as np
except ImportError:
    # Se numpy não estiver disponível, definir alternativas simples
    class np:
        @staticmethod
        def isnan(x):
            return x != x
        @staticmethod
        def isinf(x):
            return x == float('inf') or x == float('-inf')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações
CONTAHUB_LOGIN_URL = "https://sp.contahub.com/rest/contahub.cmds.UsuarioCmd/login/17421701611337?emp=0"
CONTAHUB_EMAIL = "digao@3768"
CONTAHUB_SENHA = "Geladeira@001"

# PLANILHAS HÍBRIDAS - NOVA CONFIGURAÇÃO
HYBRID_SHEETS = {
    "vendas": {
        "id": "1eI11IWdwUce_2P27eKoltMT19D4Dvgv6wb7T8HNv6DY",
        "name": "Vendas_ordinario",
        "modules": ["Analitico", "Pagamentos", "FatPorHora"]
    },
    "fiscal": {
        "id": "1Dk4mOHfx5FsxTVhsqnYF-todecmUVvbOqaF69s14YTY", 
        "name": "Fiscal_ordinario",
        "modules": ["NF", "Periodo"]
    },
    "operacional": {
        "id": "1FZPQtQXN_To5qgJVHYu7o55A0TXRf8hj7UABUTsMrTY",
        "name": "Operacional_ordinario", 
        "modules": ["Tempo", "VisaoCompetencia"]
    }
}

# Mapeamento de módulos para planilhas
MODULE_TO_SHEET = {}
for sheet_key, sheet_info in HYBRID_SHEETS.items():
    for module in sheet_info["modules"]:
        MODULE_TO_SHEET[module] = sheet_key

# Configurações de Visão de Competência
CONTA_AZUL_EMAIL = "rodrigo@grupomenosemais.com.br"
CONTA_AZUL_SENHA = "Ca12345@"
SECRET_2FA = "PKB7MTXCP5M3Y54C6KGTZFMXONAGOLQDUKGDN3LF5U4XAXNULP4A"

# Download paths - diferentes para Windows e AWS
if os.name == 'nt':  # Windows
    DOWNLOAD_PATH = os.path.join(os.getcwd(), "downloads")
else:  # Linux/AWS
    DOWNLOAD_PATH = "/tmp"

# Criar pasta de download se não existir
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

EXPORT_FILE_NAME = "visao_competencia.xls"

# Configurações AWS
AWS_REGION = 'sa-east-1'

# Configuração Discord
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1377301912201990307/WcS4kTrIbClF8V_iMY7meRKt119E-ZrEdiuu6nNKcu5KlAcMJx8RoabdXyA0Lya53X-f"

# Lista de seletores para pop-ups do Conta Azul
POPUP_SELECTORS = [
    {"popup": "a.tracksale-close-link", "description": "Pesquisa NPS"},
    {"popup": "#tracksale-wrapper button.close", "description": "Tracksale wrapper"},
    {"popup": ".modal-dialog .close", "description": "Modal genérico"},
    {"popup": ".modal-dialog button[data-dismiss='modal']", "description": "Botão dismiss modal"},
    {"popup": ".popper-container .close-btn", "description": "Popper container"},
    {"popup": ".notification-container .close-btn", "description": "Notificação"},
    {"popup": ".toast-container .close-button", "description": "Toast notification"},
    {"popup": "div[role='dialog'] button[aria-label='Close']", "description": "Dialog ARIA"}
]

def sanitize_metric_name(name):
    """Remover caracteres especiais dos nomes de métricas"""
    # Remover acentos e caracteres especiais
    name = name.replace('á', 'a').replace('ã', 'a').replace('ç', 'c')
    name = name.replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    # Manter apenas letras, números e alguns caracteres especiais permitidos
    name = re.sub(r'[^a-zA-Z0-9._-]', '', name)
    return name

def clean_data_for_sheets(data):
    """Limpar dados para o Google Sheets"""
    if isinstance(data, list):
        return [clean_data_for_sheets(item) for item in data]
    elif isinstance(data, dict):
        return {key: clean_data_for_sheets(value) for key, value in data.items()}
    elif isinstance(data, (int, float)):
        # Verificar se é NaN, infinito ou muito grande
        try:
            if math.isnan(data) or math.isinf(data) or abs(data) > 1e308:
                return ""  # Converter para string vazia
        except (TypeError, ValueError):
            # Se não conseguir verificar, assumir que é válido
            pass
        return data
    elif data is None:
        return ""
    else:
        return str(data)

def send_cloudwatch_metric(metric_name, value, unit='Count'):
    """Enviar métrica para CloudWatch"""
    try:
        cloudwatch = boto3.client('cloudwatch', region_name=AWS_REGION)
        cloudwatch.put_metric_data(
            Namespace='TesteFinal',
            MetricData=[
                {
                    'MetricName': sanitize_metric_name(metric_name),
                    'Value': value,
                    'Unit': unit,
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
        logger.info(f"✅ Métrica enviada: {sanitize_metric_name(metric_name)} = {value}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar métrica: {e}")

def login_contahub():
    """Login no ContaHub"""
    try:
        logger.info("🔐 Iniciando login no ContaHub...")
        send_cloudwatch_metric('LoginAttempt', 1)
        
        session = requests.Session()
        
        login_data = {
            "usr_email": CONTAHUB_EMAIL,
            "usr_password_sha1": hashlib.sha1(CONTAHUB_SENHA.encode()).hexdigest()
        }
        
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        })
        
        response = session.post(CONTAHUB_LOGIN_URL, data=login_data, timeout=30)
        
        if response.status_code == 200:
            logger.info("✅ Login ContaHub realizado com sucesso!")
            send_cloudwatch_metric('LoginSuccess', 1)
            return session
        else:
            logger.error(f"❌ Falha no login ContaHub: {response.status_code}")
            send_cloudwatch_metric('LoginFailed', 1)
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro no login ContaHub: {e}")
        send_cloudwatch_metric('LoginFailed', 1)
        return None

def get_google_sheets_client():
    """Configurar cliente Google Sheets para planilhas híbridas"""
    try:
        logger.info("🔗 Configurando cliente Google Sheets para planilhas híbridas...")
        
        # Caminho para credenciais (ajustar conforme necessário)
        credentials_path = "/home/ec2-user/google_credentials.json"
        
        if not os.path.exists(credentials_path):
            logger.error(f"❌ Arquivo de credenciais não encontrado: {credentials_path}")
            return None
        
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
        client = gspread.authorize(creds)
        
        # Verificar acesso às planilhas híbridas
        logger.info("🔍 Verificando acesso às planilhas híbridas...")
        for sheet_key, sheet_info in HYBRID_SHEETS.items():
            try:
                spreadsheet = client.open_by_key(sheet_info["id"])
                logger.info(f"✅ {sheet_info['name']}: Acesso confirmado")
            except Exception as e:
                logger.error(f"❌ {sheet_info['name']}: Erro de acesso - {e}")
                return None
        
        logger.info("✅ Cliente Google Sheets configurado para planilhas híbridas!")
        send_cloudwatch_metric('GoogleSheetsConnection', 1)
        return client
        
    except Exception as e:
        logger.error(f"❌ Erro ao configurar Google Sheets: {e}")
        send_cloudwatch_metric('GoogleSheetsError', 1)
        return None

def get_hybrid_spreadsheet(client, module_name):
    """Obter a planilha correta baseada no módulo"""
    if module_name not in MODULE_TO_SHEET:
        logger.error(f"❌ Módulo {module_name} não mapeado para planilha híbrida")
        return None
    
    sheet_key = MODULE_TO_SHEET[module_name]
    sheet_info = HYBRID_SHEETS[sheet_key]
    
    try:
        spreadsheet = client.open_by_key(sheet_info["id"])
        logger.info(f"📊 Usando planilha híbrida: {sheet_info['name']} para módulo {module_name}")
        return spreadsheet
    except Exception as e:
        logger.error(f"❌ Erro ao abrir planilha híbrida {sheet_info['name']}: {e}")
        return None

def fetch_data_contahub(session, consulta_config, start_date, end_date):
    """Buscar dados de uma consulta específica do ContaHub"""
    try:
        nome = consulta_config['nome']
        base_url = consulta_config['url']
        qry = consulta_config['qry']
        params = consulta_config.get('params', '')
        
        logger.info(f"📡 Buscando dados: {nome} ({start_date} - {end_date})")
        
        # Construir URL completa
        query_url = f"{base_url}?qry={qry}&d0={start_date}&d1={end_date}&emp=3768&nfe=1{params}"
        
        logger.info(f"🔗 URL: {query_url}")
        
        response = session.get(query_url, timeout=60)
        
        if response.status_code != 200:
            logger.error(f"❌ Erro HTTP {response.status_code} para {nome}")
            send_cloudwatch_metric(f'{nome}QueryFailed', 1)
            return None
        
        data = response.json()
        
        if isinstance(data, dict) and 'list' in data:
            records = data['list']
            count = len(records)
            logger.info(f"✅ {nome}: {count} registros encontrados")
            send_cloudwatch_metric(f'{nome}RecordsFound', count)
            return records
        else:
            logger.warning(f"⚠️  {nome}: Formato de resposta inesperado")
            send_cloudwatch_metric(f'{nome}FormatError', 1)
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro ao buscar {nome}: {e}")
        send_cloudwatch_metric(f'{nome}QueryFailed', 1)
        return None

def auto_resize_worksheet(worksheet, required_rows, required_cols=None):
    """Redimensiona automaticamente a planilha conforme necessário"""
    try:
        current_rows = worksheet.row_count
        current_cols = worksheet.col_count
        
        # Calcular quantas linhas são necessárias (com margem de segurança)
        needed_rows = required_rows + 100  # Margem de 100 linhas
        needed_cols = required_cols or current_cols
        
        # Verificar se precisa redimensionar
        needs_resize = False
        new_rows = current_rows
        new_cols = current_cols
        
        if needed_rows > current_rows:
            new_rows = needed_rows
            needs_resize = True
            logger.info(f"📏 Expandindo linhas: {current_rows} → {new_rows}")
        
        if needed_cols > current_cols:
            new_cols = needed_cols
            needs_resize = True
            logger.info(f"📏 Expandindo colunas: {current_cols} → {new_cols}")
        
        # Redimensionar se necessário
        if needs_resize:
            worksheet.resize(rows=new_rows, cols=new_cols)
            logger.info(f"✅ Aba redimensionada para {new_rows}x{new_cols}")
            return True
        else:
            logger.info(f"✅ Aba já tem espaço suficiente ({current_rows}x{current_cols})")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao redimensionar aba: {e}")
        return False

def add_to_sheet(sheet, sheet_name, data, query_type, execution_stats=None):
    """Adicionar dados a uma aba específica do Google Sheets seguindo o padrão do testefinal.py"""
    try:
        logger.info(f"📊 Processando dados para {query_type} ({len(data)} registros)")
        
        # Processar dados seguindo o padrão do script original
        if query_type == "Analitico":
            formatted_data = process_data_analitico_aws(data)
        elif query_type == "NF":
            formatted_data = process_data_nf_aws(data)
        elif query_type == "Periodo":
            formatted_data = process_data_periodo_aws(data)
        elif query_type == "Tempo":
            formatted_data = process_data_tempo_aws(data)
        elif query_type == "Pagamentos":
            formatted_data = process_data_pagamentos_aws(data)
        elif query_type == "FatPorHora":
            formatted_data = process_data_fatporhora_aws(data)
        else:
            logger.error(f"❌ Tipo de consulta desconhecido: {query_type}")
            return False
        
        if not formatted_data:
            logger.warning(f"⚠️  Nenhum dado formatado para {query_type}")
            return False
        
        logger.info(f"✅ {len(formatted_data)} registros formatados para {query_type}")
        
        # Verificar se a aba existe
        try:
            worksheet = sheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            logger.info(f"📄 Criando nova aba: {sheet_name}")
            # Criar com tamanho adequado baseado nos dados
            initial_rows = len(formatted_data) + 200  # Margem de segurança
            initial_cols = len(formatted_data[0]) + 5 if formatted_data else 30
            worksheet = sheet.add_worksheet(title=sheet_name, rows=initial_rows, cols=initial_cols)
        
        # Verificar espaço atual e redimensionar se necessário
        current_data_count = len(worksheet.get_all_values())
        total_needed_rows = current_data_count + len(formatted_data)
        
        logger.info(f"📏 Verificando espaço: {current_data_count} linhas existentes + {len(formatted_data)} novas = {total_needed_rows} total")
        
        # Redimensionar automaticamente se necessário
        auto_resize_worksheet(worksheet, total_needed_rows)
        
        # Log dos primeiros registros para debug das colunas A e B
        if formatted_data and len(formatted_data) > 0:
            logger.info(f"🔍 Debug: Primeiros 3 registros de {query_type}:")
            for i, record in enumerate(formatted_data[:3]):
                if len(record) >= 2:
                    logger.info(f"  Registro {i+1}: Col A={record[0]}, Col B={record[1]}")
                else:
                    logger.info(f"  Registro {i+1}: Dados insuficientes ({len(record)} colunas)")
        
        # Adicionar dados formatados diretamente à planilha
        worksheet.append_rows(formatted_data, value_input_option='USER_ENTERED')
        
        # Calcular linhas afetadas
        last_row = len(formatted_data)
        
        logger.info(f"✅ Dados inseridos nas linhas {len(formatted_data)}")
        
        # As colunas A e B já foram calculadas e inseridas corretamente nos dados formatados
        # Não é necessário chamar update_columns_a_and_b_aws novamente
        
        # Remover duplicatas (DESABILITADO PARA SISTEMA HÍBRIDO)
        try:
            logger.info(f"🧹 Sistema híbrido - deduplicação desabilitada para {sheet_name}")
            duplicates_removed = 0  # Sistema híbrido não precisa de deduplicação manual
            
            # Atualizar estatísticas
            if execution_stats and query_type in execution_stats['modules']:
                execution_stats['modules'][query_type]['duplicates_removed'] = duplicates_removed
                execution_stats['total_duplicates_removed'] += duplicates_removed
                
        except Exception as e:
            logger.error(f"❌ Erro ao remover duplicatas: {e}")
        
        # Calcular métricas de negócio dos dados processados
        try:
            logger.info(f"📈 Calculando métricas de negócio para {query_type}...")
            business_metrics = calculate_business_metrics(formatted_data, query_type)
            
            # Armazenar métricas nas estatísticas
            if execution_stats:
                if 'business_metrics' not in execution_stats:
                    execution_stats['business_metrics'] = {}
                execution_stats['business_metrics'][query_type] = business_metrics
                
            if business_metrics:
                logger.info(f"✅ Métricas calculadas para {query_type}: {len(business_metrics)} indicadores")
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular métricas de negócio: {e}")
        
        send_cloudwatch_metric(f"{sheet_name}SheetsSuccess", 1)
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao adicionar dados em {sheet_name}: {e}")
        send_cloudwatch_metric(f"{sheet_name}SheetsError", 1)
        return False

def get_date_column_index(query_type):
    """Retorna o índice da coluna de data para cada tipo de consulta"""
    date_columns = {
        "Analitico": 13,  # vd_dtgerencial (coluna N) - índice 13
        "NF": 3,          # vd_dtgerencial (coluna D) - índice 3  
        "Periodo": 4,     # dt_gerencial (coluna E) - índice 4
        "Tempo": 30,      # dia (coluna AE) - índice 30
        "Pagamentos": 4,  # dt_gerencial (coluna E) - índice 4
        "FatPorHora": 2   # vd_dtgerencial (coluna C) - índice 2
    }
    return date_columns.get(query_type)

def process_data_analitico_aws(records):
    """Processa dados analíticos seguindo o padrão do testefinal.py original"""
    if not records:
        return []
        
    formatted_records = []
    
    for record in records:
        try:
            # Extrair a data e calcular dia da semana/semana
            vd_dtgerencial_raw = record.get('vd_dtgerencial', '')
            vd_dtgerencial_iso = vd_dtgerencial_raw.split('T')[0] if 'T' in vd_dtgerencial_raw else vd_dtgerencial_raw
            vd_dtgerencial_br = format_date_brazilian(vd_dtgerencial_iso)
            
            day_of_week, week_number = calculate_week_and_day(vd_dtgerencial_iso)  # Usar ISO para cálculos
            
            # Extrair e formatar campos exatamente como no script original
            formatted_record = [
                day_of_week,                                    # A: Dia da semana
                week_number,                                    # B: Número da semana
                record.get('vd', ''),                           # C: vd
                record.get('vd_mesadesc', ''),                  # D: vd_mesadesc
                record.get('vd_localizacao', ''),               # E: vd_localizacao
                record.get('itm', ''),                          # F: itm
                record.get('trn', ''),                          # G: trn
                record.get('trn_desc', ''),                     # H: trn_desc
                record.get('prefixo', ''),                      # I: prefixo
                record.get('tipo', ''),                         # J: tipo
                record.get('tipovenda', ''),                    # K: tipovenda
                record.get('ano', ''),                          # L: ano
                record.get('mes', ''),                          # M: mes
                vd_dtgerencial_br,                                 # N: vd_dtgerencial
                record.get('usr_lancou', ''),                   # O: usr_lancou
                record.get('prd', ''),                          # P: prd
                record.get('prd_desc', ''),                     # Q: prd_desc
                record.get('grp_desc', ''),                     # R: grp_desc
                record.get('loc_desc', ''),                     # S: loc_desc
                format_monetary(record.get('qtd', '')),         # T: qtd
                format_monetary(record.get('desconto', '')),    # U: desconto
                format_monetary(record.get('valorfinal', '')),  # V: valorfinal
                format_monetary(record.get('custo', '')),       # W: custo
                record.get('itm_obs', ''),                      # X: itm_obs
                record.get('comandaorigem', ''),                # Y: comandaorigem
                record.get('itemorigem', '')                    # Z: itemorigem
            ]
            
            formatted_records.append(formatted_record)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar registro analítico: {e}")
            continue
    
    return formatted_records

def process_data_nf_aws(records):
    """Processa dados de NF seguindo o padrão do testefinal.py original"""
    if not records:
        return []
        
    formatted_records = []
    
    for record in records:
        try:
            # Extrair e validar campos obrigatórios
            cnpj = record.get('cnpj#')
            vd_dtgerencial = record.get('vd_dtgerencial')
            nf_dtcontabil = record.get('nf_dtcontabil')
            
            if not (cnpj and vd_dtgerencial):
                continue
                
            # Extrair data para calcular dia da semana e semana do ano
            gerencial_date = vd_dtgerencial
            date_part = gerencial_date.split('T')[0] if 'T' in gerencial_date else gerencial_date
            
            # Calcular dia da semana e número da semana (usar formato ISO)
            day_of_week, week_number = calculate_week_and_day(date_part)
            
            # Formatar datas para formato brasileiro
            vd_dtgerencial_br = format_date_brazilian(date_part)
            nf_dtcontabil_br = format_date_brazilian(nf_dtcontabil.split('T')[0] if nf_dtcontabil and 'T' in nf_dtcontabil else nf_dtcontabil)
            
            # Formatar campos monetários
            valor_autorizado = parse_float(record.get('valor_autorizado', 0))
            valor_substituido = parse_float(record.get('valor_substituido_nfe_nfce', 0))
            valor_a_apurar = parse_float(record.get('valor_a_apurar', 0))
            vrst_autorizado = parse_float(record.get('vrst_autorizado', 0))
            vrisento_autorizado = parse_float(record.get('vrisento_autorizado', 0))
            valor_cancelado = parse_float(record.get('valor_cancelado', 0))
            
            # Extrair campos com validação
            nf_serie = record.get('nf_serie', '')
            nf_tipo = record.get('nf_tipo', '')
            nf_ambiente = record.get('nf_ambiente', '')
            subst_nfe_nfce = record.get('subst_nfe_nfce', '')
            cancelada = record.get('cancelada', '')
            autorizada = record.get('autorizada', '')
            inutilizada = record.get('inutilizada', '')
            
            # Limpar datas
            vd_dtgerencial_clean = date_part
            nf_dtcontabil_clean = nf_dtcontabil.split('T')[0] if nf_dtcontabil and 'T' in nf_dtcontabil else nf_dtcontabil
            
            # Montar registro formatado
            formatted_record = [
                day_of_week,                # A: Dia da semana
                week_number,                # B: Número da semana
                str(cnpj),                  # C: CNPJ
                vd_dtgerencial_br,       # D: Data gerencial
                nf_dtcontabil_br,        # E: Data contábil
                nf_tipo,                    # F: Tipo NF
                nf_ambiente,                # G: Ambiente NF
                nf_serie,                   # H: Série NF
                subst_nfe_nfce,             # I: Subst NFe NFCe
                cancelada,                  # J: Cancelada
                autorizada,                 # K: Autorizada
                inutilizada,                # L: Inutilizada
                valor_autorizado,           # M: Valor autorizado
                valor_substituido,          # N: Valor substituído
                valor_a_apurar,             # O: Valor a apurar
                vrst_autorizado,            # P: Valor ST
                vrisento_autorizado,        # Q: Valor isento
                valor_cancelado             # R: Valor cancelado
            ]
            
            formatted_records.append(formatted_record)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar registro NF: {e}")
            continue
    
    return formatted_records

def process_data_periodo_aws(records):
    """Processa dados de período seguindo o padrão do testefinal.py original"""
    if not records:
        return []
        
    formatted_records = []
    
    # Função para converter string para float seguramente
    def safe_float(value):
        if value is None:
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
            
        if isinstance(value, str):
            # Remover aspas, R$ e espaços
            clean_value = value.strip()
            if clean_value.startswith("'"):
                clean_value = clean_value[1:]
            if clean_value.startswith("R$"):
                clean_value = clean_value[2:].strip()
                
            # Se estiver vazio após limpeza
            if not clean_value or clean_value.lower() == "null" or clean_value == "0":
                return 0.0
                
            # Converter formato brasileiro
            try:
                if "," in clean_value:
                    if "." in clean_value:  # 1.234,56
                        clean_value = clean_value.replace(".", "").replace(",", ".")
                    else:  # 123,45
                        clean_value = clean_value.replace(",", ".")
                return float(clean_value)
            except ValueError:
                return 0.0
        return 0.0
    
    # Função para converter string para date seguramente
    def safe_date(value):
        if not value:
            return ""
            
        # Já é um objeto date/datetime
        if hasattr(value, 'strftime'):
            return value.strftime("%d/%m/%Y")  # Formato brasileiro
            
        # Para strings
        if isinstance(value, str):
            # Remover aspas
            clean_value = value.strip()
            if clean_value.startswith("'"):
                clean_value = clean_value[1:]
                
            # Se estiver vazio após limpeza
            if not clean_value or clean_value.lower() == "null":
                return ""
                
            # Se tiver T, pegar só a parte da data
            if "T" in clean_value:
                clean_value = clean_value.split("T")[0]
                
            # Verificar se é uma data no formato YYYY-MM-DD e converter para DD/MM/YYYY
            if len(clean_value) >= 10 and clean_value[4] == "-" and clean_value[7] == "-":
                try:
                    datetime.strptime(clean_value, "%Y-%m-%d")
                    return format_date_brazilian(clean_value)  # Converter para formato brasileiro
                except ValueError:
                    return clean_value
        return value
    
    # Função para converter string para int seguramente
    def safe_int(value):
        if value is None:
            return 0
            
        if isinstance(value, int):
            return value
            
        if isinstance(value, float):
            return int(value)
            
        if isinstance(value, str):
            # Remover aspas e espaços
            clean_value = value.strip()
            if clean_value.startswith("'"):
                clean_value = clean_value[1:]
                
            # Se estiver vazio após limpeza
            if not clean_value or clean_value.lower() == "null":
                return 0
                
            try:
                return int(float(clean_value))
            except ValueError:
                return 0
        return 0
    
    # Processar registros
    for record in records:
        try:
            # Extrair dados principais
            vd = record.get("vd", "")
            dt_gerencial_raw = record.get("dt_gerencial", "")
            
            # Validar os campos obrigatórios
            if not vd or not dt_gerencial_raw:
                continue
            
            # Extrair data ISO para cálculos (antes da formatação brasileira)
            dt_gerencial_iso = dt_gerencial_raw.split('T')[0] if 'T' in dt_gerencial_raw else dt_gerencial_raw
            
            # Calcular dia da semana e número da semana baseado na data ISO
            day_of_week, week_number = calculate_week_and_day(dt_gerencial_iso)
            
            # Formatar data para formato brasileiro
            dt_gerencial_br = safe_date(dt_gerencial_raw)
            
            # Extrair e limpar dados conforme estrutura da planilha:
            # Dia Semana | Semana | vd | trn | dt_gerencial | tipovenda | vd_mesadesc | vd_localizacao | 
            # cht_fonea | cht_nome | cli | cli_nome | cli_cpf | cli_dtnasc | cli_email | usr_abriu | 
            # pessoas | qtd_itens | vr_pagamentos | vr_produtos | vr_repique | vr_couvert | vr_desconto | 
            # motivo | dt_contabil | ultimo_pedido | vd_cpf | nf_autorizada | nf_chaveacesso | nf_dtcontabil | vd_dtcontabil
            
            row = [
                day_of_week,                                                           # A: Dia da semana
                week_number,                                                           # B: Número da semana  
                str(vd).strip(),                                                       # C: vd
                str(record.get("trn", "")).strip(),                                   # D: trn
                dt_gerencial_br,                                                       # E: dt_gerencial
                str(record.get("tipovenda", "")).strip(),                            # F: tipovenda
                str(record.get("vd_mesadesc", "")).strip(),                          # G: vd_mesadesc
                str(record.get("vd_localizacao", "")).strip(),                       # H: vd_localizacao (mantido para compatibilidade)
                str(record.get("cht_fonea", "")).strip(),                            # I: cht_fonea (novo campo)
                str(record.get("cht_nome", "")).strip(),                             # J: cht_nome (novo campo)
                safe_int(record.get("cli", 0)),                                      # K: cli
                str(record.get("cli_nome", "")).strip(),                             # L: cli_nome
                str(record.get("cli_cpf", "")).strip(),                              # M: cli_cpf (novo campo)
                safe_date(record.get("cli_dtnasc", "")),                             # N: cli_dtnasc
                str(record.get("cli_email", "")).strip(),                            # O: cli_email (novo campo)
                str(record.get("usr_abriu", "")).strip(),                            # P: usr_abriu
                safe_int(record.get("pessoas", 0)),                                  # Q: pessoas
                safe_int(record.get("qtd_itens", 0)),                                # R: qtd_itens
                # Campos monetários com $ no início
                safe_float(record.get("$vr_pagamentos", 0)) or safe_float(record.get("vr_pagamentos", 0)),     # S: vr_pagamentos
                safe_float(record.get("$vr_produtos", 0)) or safe_float(record.get("vr_produtos", 0)),         # T: vr_produtos
                safe_float(record.get("$vr_repique", 0)) or safe_float(record.get("vr_repique", 0)),           # U: vr_repique
                safe_float(record.get("$vr_couvert", 0)) or safe_float(record.get("vr_couvert", 0)),           # V: vr_couvert
                safe_float(record.get("vr_desconto", 0)) or safe_float(record.get("$vr_desconto", 0)),         # W: vr_desconto (mantido para compatibilidade)
                str(record.get("motivo", "")).strip(),                              # X: motivo (mantido para compatibilidade)
                safe_date(record.get("dt_contabil", "")),                            # Y: dt_contabil (mantido para compatibilidade)
                safe_date(record.get("ultimo_pedido", "")),                          # Z: ultimo_pedido
                str(record.get("vd_cpf", "")).strip(),                               # AA: vd_cpf (mantido para compatibilidade)
                str(record.get("nf_autorizada", "")).strip(),                        # AB: nf_autorizada
                str(record.get("nf_chaveacesso", "")).strip(),                       # AC: nf_chaveacesso
                safe_date(record.get("nf_dtcontabil", "")),                          # AD: nf_dtcontabil
                safe_date(record.get("vd_dtcontabil", ""))                           # AE: vd_dtcontabil (mantido para compatibilidade)
            ]
            
            formatted_records.append(row)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar registro período: {e}")
            continue
    
    return formatted_records

def process_data_tempo_aws(records):
    """Processa dados de tempo seguindo o padrão do testefinal.py original"""
    if not records:
        return []
        
    formatted_records = []
    
    # Processar cada registro
    for record in records:
        try:
            # Extrair dados diretamente do JSON conforme estrutura real
            # Campos de identificação básicos
            vd = record.get('vd', '')
            itm = record.get('itm', '')
            
            # Campos de descrição
            grp_desc = record.get('grp_desc', '')
            prd_desc = record.get('prd_desc', '')
            vd_mesadesc = record.get('vd_mesadesc', '')
            vd_localizacao = record.get('vd_localizacao', '')
            loc_desc = record.get('loc_desc', '')
            
            # Campos de tempo
            t0_lancamento = record.get('t0-lancamento', '')
            t1_prodini = record.get('t1-prodini', '')
            t2_prodfim = record.get('t2-prodfim', '')
            t3_entrega = record.get('t3-entrega', '')
            
            # Campos calculados de diferença de tempo
            t0_t1 = record.get('t0-t1', '')
            t0_t2 = record.get('t0-t2', '')
            t0_t3 = record.get('t0-t3', '')
            t1_t2 = record.get('t1-t2', '')
            t1_t3 = record.get('t1-t3', '')
            t2_t3 = record.get('t2-t3', '')
            
            # Campos adicionais
            prd = record.get('prd', '')
            prd_idexterno = record.get('prd_idexterno', '')
            usr_abriu = record.get('usr_abriu', '')
            usr_lancou = record.get('usr_lancou', '')
            usr_produziu = record.get('usr_produziu', '')
            usr_entregou = record.get('usr_entregou', '')
            usr_transfcancelou = record.get('usr_transfcancelou', '')
            prefixo = record.get('prefixo', '')
            tipovenda = record.get('tipovenda', '')
            
            # Campos de data e tempo
            ano = record.get('ano', '')
            mes = record.get('mes', '')
            dia_raw = record.get('dia', '')
            dds = record.get('dds', '')
            diadasemana = record.get('diadasemana', '')
            hora = record.get('hora', '')
            
            # Quantidade
            itm_qtd = record.get('itm_qtd', '')
            
            # Extrair dia da semana e número da semana da data
            if dia_raw:
                # Extrair data ISO para cálculos (antes da formatação brasileira)
                dia_iso = dia_raw.split('T')[0] if 'T' in dia_raw else dia_raw
                day_of_week, week_number = calculate_week_and_day(dia_iso)
                dia_br = format_date_brazilian(dia_iso)  # Converter para formato brasileiro
            else:
                day_of_week, week_number = '', ''
                dia_br = ''
            
            # Criar registro formatado - 35 colunas (A até AI)
            formatted_record = [
                day_of_week,  # Coluna A - dia_semana
                week_number,  # Coluna B - semana
                grp_desc,     # Coluna C - grp_desc
                prd_desc,     # Coluna D - prd_desc
                vd,           # Coluna E - vd
                itm,          # Coluna F - itm
                t0_lancamento,# Coluna G - t0_lancamento
                t1_prodini,   # Coluna H - t1_prodini
                t2_prodfim,   # Coluna I - t2_prodfim
                t3_entrega,   # Coluna J - t3_entrega
                t0_t1,        # Coluna K - t0_t1
                t0_t2,        # Coluna L - t0_t2
                t0_t3,        # Coluna M - t0_t3
                t1_t2,        # Coluna N - t1_t2
                t1_t3,        # Coluna O - t1_t3
                t2_t3,        # Coluna P - t2_t3
                prd,          # Coluna Q - prd
                prd_idexterno,# Coluna R - prd_idexterno
                loc_desc,     # Coluna S - loc_desc
                vd_mesadesc,  # Coluna T - vd_mesadesc
                vd_localizacao,# Coluna U - vd_localizacao
                usr_abriu,    # Coluna V - usr_abriu
                usr_lancou,   # Coluna W - usr_lancou
                usr_produziu, # Coluna X - usr_produziu
                usr_entregou, # Coluna Y - usr_entregou
                usr_transfcancelou, # Coluna Z - usr_transfcancelou
                prefixo,      # Coluna AA - prefixo
                tipovenda,    # Coluna AB - tipovenda
                ano,          # Coluna AC - ano
                mes,          # Coluna AD - mes
                dia_br,       # Coluna AE - dia
                dds,          # Coluna AF - dds
                diadasemana,  # Coluna AG - diadasemana
                hora,         # Coluna AH - hora
                itm_qtd       # Coluna AI - itm_qtd
            ]
            
            formatted_records.append(formatted_record)
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar registro tempo: {e}")
            continue
    
    return formatted_records

def process_data_pagamentos_aws(records):
    """Processa dados de pagamentos seguindo o padrão do testefinal.py original"""
    if not records:
        return []
        
    formatted_records = []
    total_liquido = 0  # Variável para somar os valores da coluna liquido
    
    # Processar cada registro
    for record in records:
        try:
            # Extrair dia da semana e número da semana da data
            dt_gerencial = record.get('dt_gerencial', '')
            dt_gerencial_iso = dt_gerencial.split('T')[0] if 'T' in dt_gerencial else dt_gerencial
            day_of_week, week_number = calculate_week_and_day(dt_gerencial_iso)
            dt_gerencial_br = format_date_brazilian(dt_gerencial_iso)
            
            # Extrair campos diretamente do JSON
            dt_transacao = record.get('dt_transacao', '')
            dt_transacao_br = format_date_brazilian(dt_transacao)
            dt_credito = record.get('dt_credito', '')
            dt_credito_br = format_date_brazilian(dt_credito)
            hr_lancamento = record.get('hr_lancamento', '')
            hr_transacao = record.get('hr_transacao', '')
            trn = record.get('trn', '')
            vd = record.get('vd', '')
            mesa = record.get('mesa', '')
            cli = record.get('cli', '')
            cliente = record.get('cliente', '')
            pag = record.get('pag', '')
            tipo = record.get('tipo', '')
            meio = record.get('meio', '')
            cartao = record.get('cartao', '')
            autorizacao = record.get('autorizacao', '')
            usr_abriu = record.get('usr_abriu', '')
            usr_lancou = record.get('usr_lancou', '')
            usr_aceitou = record.get('usr_aceitou', '')
            motivodesconto = record.get('motivodesconto', '')
            
            # Processar valores monetários - usar os valores com prefixo $ se disponíveis
            vr_pagamentos = format_monetary(record.get('$vr_pagamentos', record.get('vr_pagamentos', '')))
            valor = format_monetary(record.get('$valor', record.get('valor', '')))
            taxa = format_monetary(record.get('$taxa', record.get('taxa', '')))
            perc = record.get('perc', '')
            liquido = format_monetary(record.get('$liquido', record.get('liquido', '')))
            
            # Somar o valor de liquido para o total
            try:
                liquido_raw = record.get('$liquido', record.get('liquido', '0'))
                if isinstance(liquido_raw, str):
                    liquido_raw = liquido_raw.replace(',', '.')
                liquido_float = float(liquido_raw)
                total_liquido += liquido_float
            except (ValueError, TypeError):
                pass  # Ignorar valores inválidos
            
            # Formatar registro para o Google Sheets - 26 colunas (A até Z)
            formatted_record = [
                day_of_week,          # A: Dia da semana como número
                week_number,          # B: Número da semana
                vd,                   # C: vd
                trn,                  # D: trn
                dt_gerencial_br,      # E: dt_gerencial
                hr_lancamento,        # F: hr_lancamento
                hr_transacao,         # G: hr_transacao
                dt_transacao_br,      # H: dt_transacao
                mesa,                 # I: mesa
                cli,                  # J: cli
                cliente,              # K: cliente
                vr_pagamentos,        # L: vr_pagamentos
                pag,                  # M: pag
                valor,                # N: valor
                taxa,                 # O: taxa
                perc,                 # P: perc
                liquido,              # Q: liquido
                tipo,                 # R: tipo
                meio,                 # S: meio
                cartao,               # T: cartao
                autorizacao,          # U: autorizacao
                dt_credito_br,        # V: dt_credito
                usr_abriu,            # W: usr_abriu
                usr_lancou,           # X: usr_lancou
                usr_aceitou,          # Y: usr_aceitou
                motivodesconto        # Z: motivodesconto
            ]
            
            formatted_records.append(formatted_record)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar registro pagamentos: {e}")
            continue
    
    # Log da soma total da coluna liquido
    logger.info(f"💰 SOMA TOTAL LIQUIDO: R$ {total_liquido:.2f} ({len(formatted_records)} registros)")
    
    return formatted_records

def process_data_fatporhora_aws(records):
    """Processa dados de faturamento por hora seguindo o padrão do testefinal.py original"""
    if not records:
        return []
        
    formatted_records = []
    
    for record in records:
        try:
            # Extrair a data do registro (vd_dtgerencial)
            vd_dtgerencial_raw = record.get('vd_dtgerencial', '')
            
            # Se vd_dtgerencial estiver vazio, usar a data atual
            if not vd_dtgerencial_raw:
                vd_dtgerencial_iso = datetime.now().date().isoformat()
                logger.warning(f"Data gerencial vazia, usando data atual: {vd_dtgerencial_iso}")
            else:
                # Extrair apenas a parte da data do timestamp
                vd_dtgerencial_iso = vd_dtgerencial_raw.split('T')[0] if 'T' in vd_dtgerencial_raw else vd_dtgerencial_raw
                
                # Validar o formato da data
                try:
                    datetime.strptime(vd_dtgerencial_iso, '%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Data inválida ({vd_dtgerencial_iso}), usando data atual")
                    vd_dtgerencial_iso = datetime.now().date().isoformat()
            
            # Converter para formato brasileiro
            vd_dtgerencial_br = format_date_brazilian(vd_dtgerencial_iso)
            
            # Calcular dia da semana e número da semana
            day_of_week, week_number = calculate_week_and_day(vd_dtgerencial_iso)
# Extrair campos diretamente do JSON
            dds = record.get('dds', '')
            dia = record.get('dia', '')
            hora = record.get('hora', '')
            qtd = record.get('qtd', 0)
            valor = format_monetary(record.get('$valor', record.get('valor', 0)))
            
            # Formatar registro para o Google Sheets - 8 colunas (A até H)
            formatted_record = [
                day_of_week,          # A: Dia da semana (número)
                week_number,          # B: Número da semana
                vd_dtgerencial_br,       # C: Data gerencial
                dds,                  # D: Dia da semana (abreviação)
                dia,                  # E: Dia da semana (texto)
                hora,                 # F: Hora
                qtd,                  # G: Quantidade
                valor                 # H: Valor
            ]
            
            formatted_records.append(formatted_record)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar registro faturamento por hora: {e}")
            continue
    
    return formatted_records

def update_columns_a_and_b(client, worksheet_name, date_column_index, new_data_start_row, new_data_end_row):
    """
    FUNÇÃO DESABILITADA - Atualiza colunas A e B para sistema híbrido.
    No sistema híbrido, as colunas A e B são calculadas durante o processamento dos dados.
    """
    logger.info(f"📅 Sistema híbrido - colunas A e B calculadas automaticamente para {worksheet_name}")
    return True

def update_columns_a_and_b_aws(sheet_name, date_column_index, start_row, end_row):
    """Atualiza colunas A e B com dia_da_semana e numero_da_semana"""
    try:
        logger.info(f"📅 Atualizando colunas A e B para {sheet_name} (linhas {start_row}-{end_row})")
        
        # Criar cliente separado
        client = gspread.authorize(Credentials.from_service_account_file("/home/ec2-user/google_credentials.json", scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]))
        
        update_columns_a_and_b(client, sheet_name, date_column_index, start_row, end_row)
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar colunas A e B: {e}")

# DISABLED - OLD FUNCTION
def remove_duplicates_from_sheet(client, worksheet_name):
    """
    FUNÇÃO DESABILITADA - Remove registros duplicados da planilha.
    Não utilizada no sistema híbrido.
    """
    logger.info(f"🧹 Sistema híbrido - deduplicação desabilitada para {worksheet_name}")
    return 0

# DISABLED - OLD FUNCTION  
def remove_duplicates_from_sheet_with_stats(client, worksheet_name):
    """
    FUNÇÃO DESABILITADA - Remove registros duplicados da planilha e retorna estatísticas.
    Não utilizada no sistema híbrido.
    """
    logger.info(f"🧹 Sistema híbrido - deduplicação desabilitada para {worksheet_name}")
    return 0

def send_discord_notification(webhook_url, execution_summary):
    """Enviar notificação para Discord com resumo da execução"""
    if not webhook_url:
        logger.info("📱 Discord webhook não configurado - notificação pulada")
        return False
    
    try:
        # Determinar cor do embed baseado no status
        if execution_summary['success_rate'] >= 90:
            color = 0x00ff00  # Verde - Sucesso
        elif execution_summary['success_rate'] >= 70:
            color = 0xffff00  # Amarelo - Aviso
        else:
            color = 0xff0000  # Vermelho - Erro
        
        # Preparar embed do Discord
        embed = {
            "embeds": [
                {
                    "title": "🚀 TesteFinal AWS - Relatório de Execução",
                    "description": f"**Status:** {'✅ Sucesso' if execution_summary['success_rate'] >= 80 else '⚠️ Problemas' if execution_summary['success_rate'] >= 50 else '❌ Falha'}",
                    "color": color,
                    "fields": [
                        {
                            "name": "📊 Resumo Geral",
                            "value": f"• **Taxa de Sucesso:** {execution_summary['success_rate']:.1f}%\n• **Registros Processados:** {execution_summary['total_records']:,}\n• **Duplicatas Removidas:** {execution_summary.get('total_duplicates_removed', 0):,}\n• **Tempo de Execução:** {execution_summary['execution_time']}\n• **Data/Hora:** {execution_summary['timestamp']}",
                            "inline": False
                        },
                        {
                            "name": "📋 Detalhes por Módulo",
                            "value": execution_summary['modules_details'],
                            "inline": False
                        },
                        {
                            "name": "📊 Uso da Planilha",
                            "value": execution_summary['spreadsheet_usage'],
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": f"AWS EC2 • Região: {AWS_REGION} • IP: {execution_summary.get('server_ip', 'N/A')}"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
        # Adicionar métricas de negócio se disponíveis
        if execution_summary.get('business_metrics'):
            business_metrics_text = format_business_metrics_for_discord(execution_summary)
            if business_metrics_text and len(business_metrics_text) > 0:
                # Dividir métricas em chunks para evitar limite de caracteres
                chunks = []
                current_chunk = ""
                lines = business_metrics_text.split('\n')
                
                for line in lines:
                    if len(current_chunk + line + '\n') > 1000:  # Limite do Discord
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = line + '\n'
                    else:
                        current_chunk += line + '\n'
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Adicionar chunks como campos separados
                for i, chunk in enumerate(chunks[:3]):  # Máximo 3 campos de métricas
                    field_name = "📈 Métricas de Negócio" if i == 0 else f"📈 Métricas (cont. {i+1})"
                    embed["embeds"][0]["fields"].append({
                        "name": field_name,
                        "value": chunk,
                        "inline": False
                    })
        
        # Adicionar campo de erros se houver
        if execution_summary.get('errors'):
            embed["embeds"][0]["fields"].append({
                "name": "❌ Erros Encontrados",
                "value": execution_summary['errors'][:1000],  # Limitar tamanho
                "inline": False
            })
        
        # Enviar para Discord
        response = requests.post(webhook_url, json=embed, timeout=10)
        
        if response.status_code == 204:
            logger.info("✅ Notificação Discord enviada com sucesso!")
            send_cloudwatch_metric('DiscordNotificationSuccess', 1)
            return True
        else:
            logger.error(f"❌ Erro ao enviar Discord: Status {response.status_code}")
            send_cloudwatch_metric('DiscordNotificationFailed', 1)
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar notificação Discord: {e}")
        send_cloudwatch_metric('DiscordNotificationFailed', 1)
        return False

def get_server_ip():
    """Obter IP do servidor AWS"""
    try:
        response = requests.get('http://checkip.amazonaws.com', timeout=5)
        return response.text.strip()
    except:
        return "N/A"

def get_date_range(use_fixed_dates=False, custom_start_date=None, custom_end_date=None):
    """Obter intervalo de datas"""
    
    # Prioridade: 1) Datas customizadas, 2) Datas fixas, 3) Ontem
    if custom_start_date:
        try:
            # Validar formato da data
            start_date = datetime.strptime(custom_start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            
            if custom_end_date:
                end_date = datetime.strptime(custom_end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            else:
                end_date = start_date  # Se não informou fim, usa a mesma data
            
            logger.info(f"📅 Usando datas customizadas: {start_date} até {end_date}")
            return start_date, end_date
            
        except ValueError:
            logger.error(f"❌ Formato de data inválido. Use YYYY-MM-DD")
            logger.info("📅 Usando data padrão (ontem) devido ao erro")
    
    if use_fixed_dates:
        # Usar data fixa para testes (sábado 24/05/2025 que sabemos que tem dados)
        fixed_date = "2025-05-24"
        logger.info(f"📅 Usando data fixa para teste: {fixed_date}")
        return fixed_date, fixed_date
    
    # Usar ontem (comportamento padrão para produção)
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')
    logger.info(f"📅 Usando data de ontem: {date_str}")
    return date_str, date_str

def calculate_week_and_day(date_str):
    """Converte 'YYYY-MM-DD' em (dia_da_semana, numero_da_semana)."""
    try:
        # Remover aspas simples no início se existir
        if isinstance(date_str, str) and date_str.startswith("'"):
            date_str = date_str[1:]
            
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
        day_of_week = parsed_date.isoweekday()       # 1=Segunda, 7=Domingo
        week_number = parsed_date.isocalendar()[1]   # Número da semana no ano
        return day_of_week, week_number
    except ValueError:
        return "", ""

def format_monetary(value):
    """Converte valor monetário para float, mantendo precisão numérica."""
    try:
        # Se for vazio ou None, retornar 0
        if value is None or value == "" or value == "None":
            return 0.0
            
        # Se for um dicionário ou lista, não é um valor monetário válido
        if isinstance(value, (dict, list)):
            return 0.0
            
        # Se já for um float, usar diretamente
        if isinstance(value, float):
            return round(value, 2)
            
        # Verificar se começa com aspas simples e remover
        if isinstance(value, str) and value.startswith("'"):
            value = value[1:]
            
        # Se começa com R$, remover para processamento
        if isinstance(value, str) and value.startswith("R$"):
            value = value[2:].strip()
            
        # Usar parse_float para converter para float
        value_float = parse_float(value)
        
        # Retornar valor float arredondado para 2 casas decimais
        return round(value_float, 2)
    except Exception as e:
        logger.error(f"Erro ao formatar valor monetário '{value}': {str(e)}")
        # Em caso de erro, retornar 0
        return 0.0

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

def optimize_worksheet_size(worksheet):
    """Otimiza o tamanho da planilha removendo linhas e colunas vazias desnecessárias"""
    try:
        # Obter todos os dados
        all_values = worksheet.get_all_values()
        
        if not all_values:
            logger.info("📏 Planilha vazia, mantendo tamanho mínimo")
            worksheet.resize(rows=100, cols=30)
            return
        
        # Encontrar a última linha com dados
        last_row_with_data = 0
        for i, row in enumerate(all_values):
            if any(cell.strip() for cell in row if cell):
                last_row_with_data = i + 1
        
        # Encontrar a última coluna com dados
        last_col_with_data = 0
        for row in all_values:
            for j, cell in enumerate(row):
                if cell.strip():
                    last_col_with_data = max(last_col_with_data, j + 1)
        
        # Calcular novo tamanho com margem de segurança
        optimal_rows = max(last_row_with_data + 50, 100)  # Mínimo 100 linhas
        optimal_cols = max(last_col_with_data + 5, 30)    # Mínimo 30 colunas
        
        current_rows = worksheet.row_count
        current_cols = worksheet.col_count
        
        # Redimensionar se necessário
        if optimal_rows != current_rows or optimal_cols != current_cols:
            worksheet.resize(rows=optimal_rows, cols=optimal_cols)
            logger.info(f"📏 Aba otimizada: {current_rows}x{current_cols} → {optimal_rows}x{optimal_cols}")
            return True
        else:
            logger.info(f"📏 Aba já está otimizada ({current_rows}x{current_cols})")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao otimizar aba: {e}")
        return False

def check_and_close_popups(driver, wait):
    """Verifica e fecha qualquer pop-up que possa estar presente na página"""
    logger.debug("🔍 Verificando possíveis pop-ups...")
    
    # Primeiro, tenta remover overlays via JavaScript
    try:
        driver.execute_script("""
            // Remove elementos comuns de overlay
            const elements = [
                'tracksale-wrapper', 
                'tracksale-content',
                'modal-backdrop',
                'modal-dialog'
            ];
            
            elements.forEach(id => {
                const el = document.getElementById(id);
                if(el) el.remove();
            });
            
            // Remove classes de modal do body
            document.body.classList.remove('modal-open');
        """)
    except Exception as e:
        logger.debug(f"Erro ao executar script de remoção: {e}")
    
    # Tenta fechar cada tipo de pop-up conhecido
    popups_found = False
    for selector in POPUP_SELECTORS:
        try:
            close_button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector["popup"]))
            )
            logger.debug(f"Pop-up encontrado: {selector['description']}")
            driver.execute_script("arguments[0].click();", close_button)
            logger.info(f"Pop-up {selector['description']} fechado com sucesso")
            popups_found = True
            time.sleep(0.5)  # Pequena pausa após fechar um pop-up
        except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
            pass
    
    if not popups_found:
        logger.debug("Nenhum pop-up encontrado")
    
    return popups_found

def process_visao_competencia():
    """Processar dados de Visão de Competência do Conta Azul - Versão Melhorada"""
    if not SELENIUM_AVAILABLE:
        logger.error("❌ Selenium não disponível - impossível processar Visão de Competência")
        return None
    
    logger.info("🔄 Iniciando processamento de Visão de Competência...")
    
    # Configurar Chrome headless para AWS
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # Configurar pasta de download
    prefs = {
        "download.default_directory": DOWNLOAD_PATH,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = None
    max_retries = 2
    
    for attempt in range(max_retries):
        logger.info(f"🔄 Tentativa {attempt + 1} de {max_retries}")
        
        try:
            driver = webdriver.Chrome(options=options)
            wait = WebDriverWait(driver, 30)
            
            # 1) Acessar a página de login
            logger.info("🔐 Acessando página de Login da Conta Azul...")
            driver.get("https://login.contaazul.com/#/")
            time.sleep(3)
            
            # Verificar e fechar pop-ups antes do login
            check_and_close_popups(driver, wait)
            
            logger.info("📝 Preenchendo credenciais...")
            
            # Encontrar e preencher email
            try:
                email_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='email']")))
                email_input.clear()
                email_input.send_keys(CONTA_AZUL_EMAIL)
                logger.info(f"✅ Email preenchido")
            except TimeoutException:
                logger.error("❌ Campo de email não encontrado")
                continue
            
            # Encontrar e preencher senha
            try:
                password_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
                password_input.clear()
                password_input.send_keys(CONTA_AZUL_SENHA)
                logger.info("✅ Senha preenchida")
            except TimeoutException:
                logger.error("❌ Campo de senha não encontrado")
                continue
            
            # Verificar pop-ups novamente
            check_and_close_popups(driver, wait)
            
            # Clicar no botão de login
            try:
                logger.info("🔑 Fazendo login...")
                botao_login = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
                    "button.ds-loader-button__button.ds-button.ds-button-primary.ds-button-md.ds-u-width--full")))
                botao_login.click()
                logger.info("✅ Botão de login clicado")
            except TimeoutException:
                logger.error("❌ Botão de login não encontrado")
                continue
            
            time.sleep(5)
            
            # 2) Realizar o MFA (2FA)
            logger.info("🔒 Processando 2FA...")
            totp = pyotp.TOTP(SECRET_2FA)
            codigo_2fa = totp.now()
            logger.debug(f"Código 2FA gerado: {codigo_2fa}")
            
            # Verificar pop-ups novamente
            check_and_close_popups(driver, wait)
            
            try:
                mfa_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' and @maxlength='6']")))
                mfa_input.clear()
                mfa_input.send_keys(str(codigo_2fa))
                logger.info("✅ Código 2FA inserido")
            except TimeoutException:
                logger.error("❌ Campo de 2FA não encontrado")
                continue
            
            # Verificar pop-ups novamente
            check_and_close_popups(driver, wait)
            
            try:
                botao_mfa = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
                    "button.ds-loader-button__button.ds-button.ds-button-primary.ds-button-md.ds-u-width--full")))
                botao_mfa.click()
                logger.info("✅ Botão de 2FA clicado")
            except TimeoutException:
                logger.error("❌ Botão de 2FA não encontrado")
                continue
            
            logger.info("✅ Login + MFA concluídos com sucesso.")
            time.sleep(5)  # Aumentar de 2 para 5 segundos após 2FA
            
            # Verificar pop-ups após login
            check_and_close_popups(driver, wait)
            
            # 3) Acessar a Visão de Competência
            logger.info("📊 Acessando Visão de Competência...")
            driver.get("https://app.contaazul.com/#/ca/financeiro/competencia")
            time.sleep(10)  # Aguardar carregamento da página
            
            # Verificar pop-ups após navegação
            check_and_close_popups(driver, wait)
            
            # 4) Configurar filtro para "Todo o período" ANTES de exportar
            logger.info("📅 Configurando filtro para 'Todo o período'...")
            
            try:
                filter_success = False
                
                # ESTRATÉGIA OTIMIZADA baseada no teste bem-sucedido
                # Procurar especificamente pelo dropdown de período que funcionou no teste
                logger.info("🔍 Procurando dropdown de período específico...")
                
                # OTIMIZAÇÃO: Ir direto ao dropdown de período correto
                logger.info("🎯 OTIMIZAÇÃO: Buscando diretamente o dropdown de período...")
                
                # Procurar especificamente pelo dropdown de período que sabemos que funciona
                period_dropdown = None
                try:
                    # Primeiro, tentar encontrar o dropdown específico de período
                    period_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'ds-date-period-dropdown')]")
                    for element in period_elements:
                        if element.is_displayed():
                            period_dropdown = element
                            logger.info(f"✅ Dropdown de período encontrado diretamente: {element.get_attribute('class')}")
                            break
                except Exception as e:
                    logger.debug(f"⚠️ Erro ao buscar dropdown específico: {e}")
                
                if period_dropdown:
                    # Usar diretamente o dropdown correto (sem scroll desnecessário)
                    try:
                        logger.info("🎯 USANDO DROPDOWN CORRETO diretamente...")
                        
                        # NÃO fazer scroll - manter posição atual para não esconder botão de exportação
                        # driver.execute_script("arguments[0].scrollIntoView(true);", period_dropdown)
                        
                        # Clicar no dropdown de período
                        driver.execute_script("arguments[0].click();", period_dropdown)
                        time.sleep(2)  # Aguardar abertura do dropdown
                        
                        # Procurar pela opção "Todo o período"
                        option_selectors = [
                            "//*[contains(text(), 'Todo o período')]",
                            "//*[contains(text(), 'Todo período')]", 
                            "//*[contains(text(), 'Todo')]"
                        ]
                        
                        option_found = False
                        for option_selector in option_selectors:
                            try:
                                options = driver.find_elements(By.XPATH, option_selector)
                                for option in options:
                                    if option.is_displayed() and 'todo' in option.text.lower():
                                        logger.info(f"🎯 ENCONTRADO: '{option.text}' - Clicando...")
                                        driver.execute_script("arguments[0].click();", option)
                                        logger.info(f"✅ Opção '{option.text}' selecionada!")
                                        option_found = True
                                        filter_success = True
                                        break
                                if option_found:
                                    break
                            except Exception as e:
                                logger.debug(f"⚠️ Erro na opção: {e}")
                                continue
                        
                        if not option_found:
                            logger.warning("⚠️ Opção 'Todo o período' não encontrada no dropdown correto")
                            
                    except Exception as e:
                        logger.error(f"❌ Erro ao usar dropdown correto: {e}")
                
                # Se não conseguiu com o método otimizado, usar o método original como fallback
                if not filter_success:
                    logger.info("🔄 Fallback: Usando método original de busca...")
                    
                    # Usar a estratégia que funcionou no teste: procurar elementos dropdown
                    dropdown_elements = []
                    dropdown_selectors = [
                        "//div[contains(@class, 'ds-date-period-dropdown')]",  # O que funcionou no teste
                        "//div[contains(@class, 'dropdown')]",
                        "//div[contains(@class, 'ds-dropdown')]"
                    ]
                    
                    for selector in dropdown_selectors:
                        try:
                            elements = driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed():
                                    dropdown_elements.append(element)
                                    logger.info(f"✅ Dropdown encontrado: {element.get_attribute('class')}")
                        except Exception as e:
                            logger.debug(f"⚠️ Erro no selector: {e}")
                            continue
                    
                    logger.info(f"📋 Total de dropdowns encontrados: {len(dropdown_elements)}")
                    
                    # Testar cada dropdown (seguindo a lógica do teste que funcionou)
                    for i, element in enumerate(dropdown_elements[:15]):  # Testar até 15 elementos
                        try:
                            logger.info(f"🔍 Testando dropdown {i+1}/{min(15, len(dropdown_elements))}...")
                            
                            # Scroll até o elemento
                            driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            time.sleep(1)
                            
                            # Clicar no elemento
                            driver.execute_script("arguments[0].click();", element)
                            time.sleep(2)  # Aguardar abertura do dropdown
                            
                            # Procurar pela opção "Todo o período" (exatamente como no teste)
                            option_selectors = [
                                "//*[contains(text(), 'Todo o período')]",
                                "//*[contains(text(), 'Todo período')]", 
                                "//*[contains(text(), 'Todo')]"
                            ]
                            
                            option_found = False
                            for option_selector in option_selectors:
                                try:
                                    options = driver.find_elements(By.XPATH, option_selector)
                                    for option in options:
                                        if option.is_displayed() and 'todo' in option.text.lower():
                                            logger.info(f"🎯 ENCONTRADO: '{option.text}' - Clicando...")
                                            driver.execute_script("arguments[0].click();", option)
                                            logger.info(f"✅ Opção '{option.text}' selecionada!")
                                            option_found = True
                                            filter_success = True
                                            break
                                    if option_found:
                                        break
                                except Exception as e:
                                    logger.debug(f"⚠️ Erro na opção: {e}")
                                    continue
                            
                            if filter_success:
                                break
                            
                            # Se não encontrou opções, tentar fechar dropdown
                            driver.execute_script("document.activeElement.blur();")
                            time.sleep(0.5)
                            
                        except Exception as e:
                            logger.debug(f"⚠️ Erro ao testar dropdown {i+1}: {e}")
                            continue
                
                if filter_success:
                    logger.info("✅ Filtro 'Todo o período' configurado com sucesso!")
                    
                    # AGUARDAR TEMPO ESTENDIDO para carregamento completo dos dados históricos
                    logger.info("⏳ Aguardando carregamento completo dos dados históricos...")
                    logger.info("   🕐 Fase 1: Aguardando 10 segundos iniciais...")
                    time.sleep(10)
                    
                    # Verificar se há indicadores de carregamento
                    loading_indicators = [
                        "//*[contains(@class, 'loading')]",
                        "//*[contains(@class, 'spinner')]", 
                        "//*[contains(text(), 'Carregando')]",
                        "//*[contains(text(), 'Loading')]"
                    ]
                    
                    max_wait_cycles = 6  # 6 ciclos de 5 segundos = 30 segundos total adicional
                    for cycle in range(max_wait_cycles):
                        logger.info(f"   🕐 Fase 2: Ciclo {cycle+1}/{max_wait_cycles} - Verificando carregamento...")
                        
                        still_loading = False
                        for indicator in loading_indicators:
                            try:
                                loading_elements = driver.find_elements(By.XPATH, indicator)
                                if any(el.is_displayed() for el in loading_elements):
                                    still_loading = True
                                    logger.info(f"   ⏳ Ainda carregando... (indicador: {indicator})")
                                    break
                            except:
                                continue
                        
                        if not still_loading:
                            logger.info(f"   ✅ Carregamento aparentemente concluído no ciclo {cycle+1}")
                            break
                        
                        time.sleep(5)  # Aguardar 5 segundos entre verificações
                    
                    # Aguardar mais 10 segundos de segurança após carregamento
                    logger.info("   🕐 Fase 3: Aguardando 10 segundos finais de segurança...")
                    time.sleep(10)
                    
                    # Total: 10s inicial + até 30s verificando + 10s final = até 50 segundos
                    logger.info("✅ Tempo de carregamento estendido concluído!")
                    
                    # IMPORTANTE: Rolar para o topo para garantir que o botão de exportação esteja visível
                    logger.info("📏 Rolando para o topo para garantir visibilidade do botão de exportação...")
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(2)  # Aguardar scroll
                    
                    # Verificar se a página tem mais dados agora
                    try:
                        # Procurar por indicadores de quantidade de dados
                        data_indicators = [
                            "//table//tr",
                            "//tbody//tr", 
                            "//*[contains(@class, 'data-grid')]//tr",
                            "//*[contains(@class, 'table')]//tr"
                        ]
                        
                        total_rows = 0
                        for indicator in data_indicators:
                            try:
                                rows = driver.find_elements(By.XPATH, indicator)
                                if rows:
                                    total_rows = max(total_rows, len(rows))
                            except:
                                continue
                        
                        if total_rows > 100:
                            logger.info(f"✅ Mais dados detectados: ~{total_rows} linhas na tabela")
                        else:
                            logger.warning(f"⚠️ Poucos dados detectados: ~{total_rows} linhas na tabela")
                            
                    except Exception as e:
                        logger.debug(f"Erro ao verificar quantidade de dados: {e}")
                    
                else:
                    logger.warning("⚠️ Não foi possível configurar o filtro de período")
                    logger.info("📤 Tentando exportar com configuração atual...")
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao configurar filtro de período: {e}")
                logger.info("📤 Tentando exportar com configuração atual...")
            
            # Verificar pop-ups novamente após mudança de filtro
            check_and_close_popups(driver, wait)
            
            # Tentar múltiplas estratégias para encontrar o botão de exportação
            export_success = False
            export_strategies = [
                {
                    "name": "XPath original",
                    "selector": (By.XPATH, "/html/body/caf-application-layout/div/caf-application/div/div[2]/div[2]/div/main/div/div[2]/div/section/div[2]/div/nav/div/div/div/div[2]/span[1]/button")
                },
                {
                    "name": "Texto 'Exportar'",
                    "selector": (By.XPATH, "//button[contains(text(), 'Exportar')]")
                },
                {
                    "name": "Texto 'Export'",
                    "selector": (By.XPATH, "//button[contains(text(), 'Export')]")
                },
                {
                    "name": "Atributo title Export",
                    "selector": (By.XPATH, "//button[contains(@title, 'Export') or contains(@title, 'Exportar')]")
                },
                {
                    "name": "Classe download",
                    "selector": (By.XPATH, "//button[contains(@class, 'download')]")
                },
                {
                    "name": "Span com Export",
                    "selector": (By.XPATH, "//span[contains(text(), 'Export') or contains(text(), 'Exportar')]/parent::button")
                }
            ]
            
            for strategy in export_strategies:
                if export_success:
                    break
                    
                try:
                    logger.info(f"📤 Tentando: {strategy['name']}...")
                    exportar_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(strategy['selector'])
                    )
                    driver.execute_script("arguments[0].click();", exportar_btn)
                    logger.info(f"✅ {strategy['name']} funcionou!")
                    export_success = True
                except TimeoutException:
                    logger.debug(f"⚠️ {strategy['name']} falhou")
            
            if not export_success:
                logger.error("❌ Nenhuma estratégia de exportação funcionou")
                continue
            
            # Se chegou aqui, o botão foi clicado
            logger.info("⬇️ Aguardando o download do arquivo...")
            time.sleep(20)
            
            # Verificar se o arquivo foi baixado em múltiplas localizações possíveis
            possible_paths = [
                os.path.join(DOWNLOAD_PATH, EXPORT_FILE_NAME),
                os.path.join(os.path.expanduser("~"), "Downloads", EXPORT_FILE_NAME),
                os.path.join(os.getcwd(), EXPORT_FILE_NAME),
                os.path.join(os.getcwd(), "downloads", EXPORT_FILE_NAME)
            ]
            
            found_file = None
            for file_path in possible_paths:
                if os.path.exists(file_path):
                    found_file = file_path
                    logger.info(f"✅ Arquivo encontrado em: {file_path}")
                    break
            
            if found_file:
                logger.info(f"📊 Tamanho: {os.path.getsize(found_file)} bytes")
                
                # Tentar ler o arquivo
                try:
                    df = pd.read_excel(found_file, engine='openpyxl')
                    df = df.fillna("")  # Substitui valores NaN por string vazia
                    
                    logger.info(f"📊 DataFrame shape: {df.shape}")
                    logger.info(f"📋 DataFrame columns: {len(df.columns)} colunas")
                    
                    # Converter para formato compatível
                    data = [df.columns.tolist()] + df.values.tolist()
                    
                    # Limpar arquivo temporário
                    try:
                        os.remove(found_file)
                        logger.info("🗑️ Arquivo temporário removido.")
                    except:
                        pass
                    
                    logger.info(f"✅ Dados processados: {len(data)} linhas (incluindo cabeçalho)")
                    return data
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao processar arquivo: {e}")
                    if os.path.exists(found_file):
                        try:
                            os.remove(found_file)
                        except:
                            pass
                    continue
            else:
                logger.error("❌ Arquivo exportado não encontrado em nenhuma das localizações.")
                logger.info(f"🔍 Localizações verificadas:")
                for path in possible_paths:
                    logger.info(f"  📁 {path}")
                continue
                
        except Exception as e:
            logger.error(f"❌ Erro durante tentativa {attempt + 1}: {e}")
            continue
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    logger.error("❌ Todas as tentativas de processamento da Visão de Competência falharam")
    return None

def monitor_hybrid_spreadsheet_usage_NEW(client):
    """Monitor híbrido das 3 planilhas"""
    try:
        total_cells = 0
        max_usage = 0.0
        spreadsheets_info = []
        
        logger.info("📊 Monitorando planilhas híbridas...")
        
        for sheet_key, sheet_info in HYBRID_SHEETS.items():
            try:
                spreadsheet = client.open_by_key(sheet_info["id"])
                sheet_cells = 0
                
                for worksheet in spreadsheet.worksheets():
                    sheet_cells += worksheet.row_count * worksheet.col_count
                
                usage_percent = (sheet_cells / 10000000) * 100
                total_cells += sheet_cells
                
                if usage_percent > max_usage:
                    max_usage = usage_percent
                
                sheet_data = {
                    "name": sheet_info["name"],
                    "total_cells": sheet_cells,
                    "usage_percent": usage_percent,
                    "modules": sheet_info["modules"]
                }
                spreadsheets_info.append(sheet_data)
                
                name = sheet_info.get("name", "N/A")
                logger.info(f"  📊 {name}: {sheet_cells:,} células ({usage_percent:.1f}%)")
                
            except Exception as e:
                logger.warning(f"  ⚠️ Erro na planilha: {e}")
        
        return {
            "total_cells": total_cells,
            "usage_percent": max_usage,
            "limit": 10000000,
            "status": "Híbrido",
            "spreadsheets": spreadsheets_info
        }
        
    except Exception as e:
        logger.error(f"❌ Erro monitoramento: {e}")
        return {"total_cells": 0, "usage_percent": 0.0, "limit": 10000000, "status": "Erro"}


def main():
    """Função principal"""
    # Configurar argumentos da linha de comando
    parser = argparse.ArgumentParser(description='Script AWS para extrair dados do ContaHub e Conta Azul')
    
    # Argumentos para controlar quais módulos serão executados
    parser.add_argument('--only-analitico', action='store_true', help='Processar apenas dados analíticos')
    parser.add_argument('--only-nf', action='store_true', help='Processar apenas dados de NF')
    parser.add_argument('--only-periodo', action='store_true', help='Processar apenas dados de período')
    parser.add_argument('--only-tempo', action='store_true', help='Processar apenas dados de tempo')
    parser.add_argument('--only-pagamentos', action='store_true', help='Processar apenas dados de pagamentos')
    parser.add_argument('--only-fatporhora', action='store_true', help='Processar apenas dados de faturamento por hora')
    parser.add_argument('--only-visaocompetencia', action='store_true', help='Processar apenas dados de Visão de Competência (Conta Azul)')
    
    # Outros argumentos
    parser.add_argument('--fixed-dates', action='store_true', help='Usar datas fixas (24/05/2025) em vez de ontem')
    parser.add_argument('--start-date', type=str, help='Data de início (formato: YYYY-MM-DD). Se não informada, usa ontem')
    parser.add_argument('--end-date', type=str, help='Data de fim (formato: YYYY-MM-DD). Se não informada, usa a mesma data de início')
    parser.add_argument('--no-database', action='store_true', help='Ignorar banco de dados, processar apenas Google Sheets')
    parser.add_argument('--auto', action='store_true', help='Modo automático para operações em lote')
    parser.add_argument('--verbose', action='store_true', help='Ativar modo de debug com mensagens detalhadas')
    
    # Adicionar argumentos para Discord
    parser.add_argument('--discord-webhook', type=str, help='URL do webhook Discord para notificações')
    
    # Processar argumentos
    args = parser.parse_args()
    
    # Configurar Discord webhook
    discord_webhook = args.discord_webhook or os.environ.get('DISCORD_WEBHOOK_URL') or DISCORD_WEBHOOK_URL
    
    # Configurar logging baseado em verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🔍 Modo verbose ativado")
    
    start_time = datetime.now()
    logger.info("🚀 INICIANDO TESTEFINAL AWS PRODUÇÃO - VERSÃO HÍBRIDA")
    logger.info("=" * 70)
    logger.info(f"🕒 Timestamp: {start_time}")
    logger.info(f"🌍 Região AWS: {AWS_REGION}")
    logger.info(f"📅 Datas fixas: {'Sim' if args.fixed_dates else 'Não'}")
    logger.info(f"🗄️  Banco de dados: {'Desabilitado' if args.no_database else 'Habilitado'}")
    logger.info(f"🤖 Modo automático: {'Sim' if args.auto else 'Não'}")
    logger.info(f"📱 Discord: {'Configurado' if discord_webhook else 'Desabilitado'}")
    logger.info(f"🔧 Selenium: {'Disponível' if SELENIUM_AVAILABLE else 'Indisponível'}")
    
    # Listar planilhas híbridas
    logger.info("📊 PLANILHAS HÍBRIDAS CONFIGURADAS:")
    for sheet_key, sheet_info in HYBRID_SHEETS.items():
        logger.info(f"  📈 {sheet_info['name']}: {', '.join(sheet_info['modules'])}")
    
    send_cloudwatch_metric('ExecutionStart', 1)
    
    # Inicializar estatísticas
    execution_stats = {
        'modules': {},
        'errors': [],
        'total_records': 0,
        'total_duplicates_removed': 0,
        'successful_modules': 0,
        'failed_modules': 0
    }
    
    # Verificar se está em modo específico ou completo
    specific_mode = any([
        args.only_analitico, 
        args.only_nf, 
        args.only_periodo, 
        args.only_tempo,
        args.only_pagamentos,
        args.only_fatporhora,
        args.only_visaocompetencia
    ])
    
    if specific_mode:
        logger.info("🎯 Modo específico ativado")
    else:
        logger.info("📊 Modo completo - processando todos os tipos")
    
    # Obter datas
    start_date, end_date = get_date_range(args.fixed_dates, args.start_date, args.end_date)
    
    # Login ContaHub (só se não for apenas Visão de Competência)
    session = None
    if not args.only_visaocompetencia:
        session = login_contahub()
        if not session:
            logger.error("❌ Falha no login ContaHub. Abortando.")
            send_cloudwatch_metric('ExecutionFailed', 1)
            return False
    
    # Configurar Google Sheets (só se não for --no-database)
    client = None
    if not args.no_database:
        client = get_google_sheets_client()
        if not client:
            logger.error("❌ Falha ao configurar Google Sheets. Abortando.")
            send_cloudwatch_metric('ExecutionFailed', 1)
            return False
    else:
        logger.info("📋 Google Sheets desabilitado pelo parâmetro --no-database")
    
    # Configurações das consultas ContaHub
    consultas_contahub = [
        {
            'nome': 'Analitico',
            'url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1742237860621',
            'qry': 77,
            'params': '&produto=&grupo=&local=&turno=&mesa=',
            'worksheet': 'CH_AnaliticoPP',
            'enabled': not specific_mode or args.only_analitico
        },
        {
            'nome': 'NF',
            'url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1742174377035',
            'qry': 73,
            'params': '',
            'worksheet': 'CH_NFs',
            'enabled': not specific_mode or args.only_nf
        },
        {
            'nome': 'Periodo',
            'url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1748545563327',
            'qry': 5,
            'params': '',
            'worksheet': 'CH_PeriodoPP',
            'enabled': not specific_mode or args.only_periodo
        },
        {
            'nome': 'Tempo',
            'url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1742603193885',
            'qry': 81,
            'params': '&prod=&grupo=&local=',
            'worksheet': 'CH_Tempo',
            'enabled': not specific_mode or args.only_tempo
        },
        {
            'nome': 'Pagamentos',
            'url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1742602462905',
            'qry': 7,
            'params': '&meio=',
            'worksheet': 'CH_Pagamentos',
            'enabled': not specific_mode or args.only_pagamentos
        },
        {
            'nome': 'FatPorHora',
            'url': 'https://sp.contahub.com/rest/contahub.cmds.QueryCmd/execQuery/1742694156165',
            'qry': 101,
            'params': '',
            'worksheet': 'CH_FatporHora',
            'enabled': not specific_mode or args.only_fatporhora
        }
    ]
    
    # Configuração do módulo Visão de Competência
    visao_competencia_config = {
        'nome': 'VisaoCompetencia',
        'worksheet': 'CA_VisaoCompetencia',
        'enabled': not specific_mode or args.only_visaocompetencia
    }
    
    # Filtrar apenas consultas habilitadas
    consultas_ativas = [c for c in consultas_contahub if c['enabled']]
    total_modules = len(consultas_ativas)
    
    # Adicionar Visão de Competência se habilitada
    if visao_competencia_config['enabled']:
        total_modules += 1
        
    logger.info(f"📋 Módulos a serem processados: {total_modules}")
    
    # Processar cada consulta ContaHub
    total_success = 0
    total_records = 0
    
    for consulta in consultas_ativas:
        logger.info(f"\n📊 Processando ContaHub: {consulta['nome']}")
        
        # Inicializar estatísticas do módulo
        module_stats = {
            'name': consulta['nome'],
            'records_found': 0,
            'duplicates_removed': 0,
            'success': False,
            'error': None
        }
        
        try:
            # Buscar dados
            data = fetch_data_contahub(session, consulta, start_date, end_date)
            
            if data:
                module_stats['records_found'] = len(data)
                total_records += len(data)
                execution_stats['total_records'] += len(data)
                logger.info(f"✅ {consulta['nome']}: {len(data)} registros extraídos")
                
                # Adicionar ao Google Sheets (se habilitado)
                if client and not args.no_database:
                    # Obter planilha híbrida correta
                    try:
                        spreadsheet = get_hybrid_spreadsheet(client, consulta['nome'])
                        if spreadsheet and add_to_sheet(spreadsheet, consulta['worksheet'], data, consulta['nome'], execution_stats):
                            total_success += 1
                            module_stats['success'] = True
                            execution_stats['successful_modules'] += 1
                            logger.info(f"✅ {consulta['nome']}: Dados salvos na planilha híbrida!")
                        else:
                            module_stats['error'] = "Falha no Google Sheets"
                            execution_stats['failed_modules'] += 1
                            execution_stats['errors'].append(f"{consulta['nome']}: Falha no Google Sheets")
                            logger.error(f"❌ {consulta['nome']}: Falha no Google Sheets")
                    except Exception as e:
                        error_msg = f"Erro ao processar planilha híbrida: {e}"
                        module_stats['error'] = error_msg
                        execution_stats['failed_modules'] += 1
                        execution_stats['errors'].append(f"{consulta['nome']}: {error_msg}")
                        logger.error(f"❌ {consulta['nome']}: {error_msg}")
                else:
                    # Modo sem banco ou processamento local
                    total_success += 1
                    module_stats['success'] = True
                    execution_stats['successful_modules'] += 1
                    logger.info(f"✅ {consulta['nome']}: Processado localmente")
            else:
                error_msg = "Nenhum dado retornado"
                module_stats['error'] = error_msg
                execution_stats['failed_modules'] += 1
                execution_stats['errors'].append(f"{consulta['nome']}: {error_msg}")
                logger.warning(f"⚠️ {consulta['nome']}: Nenhum dado retornado")
        
        except Exception as e:
            error_msg = f"Erro na consulta: {e}"
            module_stats['error'] = error_msg
            execution_stats['failed_modules'] += 1
            execution_stats['errors'].append(f"{consulta['nome']}: {error_msg}")
            logger.error(f"❌ {consulta['nome']}: {error_msg}")
        
        # Armazenar estatísticas do módulo
        execution_stats['modules'][consulta['nome']] = module_stats
        
        # Enviar métricas específicas do módulo
        send_cloudwatch_metric(f'Module{consulta["nome"]}Records', module_stats['records_found'])
        send_cloudwatch_metric(f'Module{consulta["nome"]}Success', 1 if module_stats['success'] else 0)
    
    # Processar Visão de Competência se habilitada
    if visao_competencia_config['enabled']:
        logger.info(f"\n🏦 Processando Conta Azul: {visao_competencia_config['nome']}")
        
        # Inicializar estatísticas do módulo
        module_stats = {
            'name': visao_competencia_config['nome'],
            'records_found': 0,
            'duplicates_removed': 0,
            'success': False,
            'error': None
        }
        
        try:
            # Processar Visão de Competência
            data = process_visao_competencia()
            
            if data:
                module_stats['records_found'] = len(data) - 1  # Subtrair cabeçalho
                total_records += len(data) - 1
                execution_stats['total_records'] += len(data) - 1
                logger.info(f"✅ {visao_competencia_config['nome']}: {len(data) - 1} registros extraídos")
                
                # Adicionar ao Google Sheets (se habilitado)
                if client and not args.no_database:
                    # Obter planilha híbrida correta
                    try:
                        spreadsheet = get_hybrid_spreadsheet(client, visao_competencia_config['nome'])
                        if spreadsheet:
                            # Para Visão de Competência, usar add_to_sheet_direct
                            worksheet_name = visao_competencia_config['worksheet']
                            try:
                                worksheet = spreadsheet.worksheet(worksheet_name)
                            except:
                                # Criar aba se não existir
                                rows = len(data)
                                cols = len(data[0]) if data else 10
                                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=rows, cols=cols)
                                logger.info(f"📋 Aba {worksheet_name} criada!")
                            
                            # Limpar e atualizar dados
                            worksheet.clear()
                            worksheet.update('A1', data, value_input_option="USER_ENTERED")
                            
                            total_success += 1
                            module_stats['success'] = True
                            execution_stats['successful_modules'] += 1
                            logger.info(f"✅ {visao_competencia_config['nome']}: Dados salvos na planilha híbrida!")
                        else:
                            module_stats['error'] = "Falha ao acessar planilha híbrida"
                            execution_stats['failed_modules'] += 1
                            execution_stats['errors'].append(f"{visao_competencia_config['nome']}: Falha ao acessar planilha híbrida")
                            logger.error(f"❌ {visao_competencia_config['nome']}: Falha ao acessar planilha híbrida")
                    except Exception as e:
                        error_msg = f"Erro ao processar planilha híbrida: {e}"
                        module_stats['error'] = error_msg
                        execution_stats['failed_modules'] += 1
                        execution_stats['errors'].append(f"{visao_competencia_config['nome']}: {error_msg}")
                        logger.error(f"❌ {visao_competencia_config['nome']}: {error_msg}")
                else:
                    # Modo sem banco ou processamento local
                    total_success += 1
                    module_stats['success'] = True
                    execution_stats['successful_modules'] += 1
                    logger.info(f"✅ {visao_competencia_config['nome']}: Processado localmente")
            else:
                error_msg = "Nenhum dado retornado ou erro no processamento"
                module_stats['error'] = error_msg
                execution_stats['failed_modules'] += 1
                execution_stats['errors'].append(f"{visao_competencia_config['nome']}: {error_msg}")
                logger.warning(f"⚠️ {visao_competencia_config['nome']}: Nenhum dado retornado")
        
        except Exception as e:
            error_msg = f"Erro no processamento: {e}"
            module_stats['error'] = error_msg
            execution_stats['failed_modules'] += 1
            execution_stats['errors'].append(f"{visao_competencia_config['nome']}: {error_msg}")
            logger.error(f"❌ {visao_competencia_config['nome']}: {error_msg}")
        
        # Armazenar estatísticas do módulo
        execution_stats['modules'][visao_competencia_config['nome']] = module_stats
        
        # Enviar métricas específicas do módulo
        send_cloudwatch_metric(f'ModuleVisaoCompetenciaRecords', module_stats['records_found'])
        send_cloudwatch_metric(f'ModuleVisaoCompetenciaSuccess', 1 if module_stats['success'] else 0)

    # Resumo final
    execution_time = datetime.now() - start_time
    success_rate = (total_success / len(consultas_ativas)) * 100 if consultas_ativas else 0
    
    logger.info(f"\n📈 RESUMO FINAL:")
    logger.info(f"✅ Consultas bem-sucedidas: {total_success}/{len(consultas_ativas)}")
    logger.info(f"📊 Total de registros processados: {total_records}")
    logger.info(f"📈 Taxa de sucesso: {success_rate:.1f}%")
    logger.info(f"⏱️  Tempo total de execução: {execution_time}")
    
    # Métricas finais
    send_cloudwatch_metric('ExecutionSuccess', total_success)
    send_cloudwatch_metric('TotalRecordsProcessed', total_records)
    send_cloudwatch_metric('ExecutionTimeSeconds', execution_time.total_seconds())
    send_cloudwatch_metric('SuccessRate', success_rate)
    
    # Preparar resumo para Discord
    try:
        # Obter IP do servidor
        server_ip = get_server_ip()
        
        # Monitorar uso de células da planilha
        usage_stats = None
        spreadsheet_usage_text = "Não disponível"
        try:
            if client and not args.no_database:
                logger.info("📊 Monitorando uso de células da planilha...")
                usage_stats = monitor_hybrid_spreadsheet_usage_NEW(client)
                if usage_stats:
                    spreadsheet_usage_text = "📊 **Planilhas Híbridas:**\n"
                    if usage_stats and "spreadsheets" in usage_stats:
                        for sheet in usage_stats["spreadsheets"]:
                            percent = sheet.get("usage_percent", 0)
                            icon = "🟢" if percent < 30 else "🟡" if percent < 70 else "🔴"
                            name = sheet.get("name", "N/A")
                            cells = sheet.get("total_cells", 0)
                            modules = ", ".join(sheet.get("modules", []))
                            spreadsheet_usage_text += f"{icon} **{name}:** {cells:,} células ({percent:.1f}%)\n"
                            spreadsheet_usage_text += f"   └─ *{modules}*\n"
                        total = usage_stats.get("total_cells", 0)
                        max_usage = usage_stats.get("usage_percent", 0)
                        spreadsheet_usage_text += f"\n📈 **Total:** {total:,} células | Maior uso: {max_usage:.1f}%"
                    else:
                        spreadsheet_usage_text += "⚠️ Sistema híbrido funcionando"
                    logger.info(f"📊 Uso total: {usage_stats['total_cells']:,} células ({usage_stats['usage_percent']:.1f}% do limite)")
        except Exception as e:
            logger.error(f"❌ Erro ao monitorar uso da planilha: {e}")
        
        # Preparar detalhes dos módulos
        modules_details = ""
        for module_name, stats in execution_stats['modules'].items():
            status_icon = "✅" if stats['success'] else "❌"
            modules_details += f"{status_icon} **{module_name}:** {stats['records_found']:,} registros"
            if stats.get('duplicates_removed', 0) > 0:
                modules_details += f" ({stats['duplicates_removed']} duplicatas removidas)"
            if stats['error']:
                modules_details += f" ({stats['error'][:50]}...)" if len(stats['error']) > 50 else f" ({stats['error']})"
            modules_details += "\n"
        
        # Preparar resumo de erros
        errors_summary = ""
        if execution_stats['errors']:
            errors_summary = "\n".join(execution_stats['errors'][:5])  # Limitar a 5 erros
            if len(execution_stats['errors']) > 5:
                errors_summary += f"\n... e mais {len(execution_stats['errors']) - 5} erros"
        
        # Preparar resumo completo para Discord
        execution_summary = {
            'success_rate': success_rate,
            'total_records': execution_stats['total_records'],
            'total_duplicates_removed': execution_stats['total_duplicates_removed'],
            'execution_time': str(execution_time).split('.')[0],  # Remover microssegundos
            'timestamp': get_brazilian_time().strftime("%d/%m/%Y %H:%M:%S"),
            'modules_details': modules_details.strip(),
            'spreadsheet_usage': spreadsheet_usage_text,
            'errors': errors_summary if errors_summary else None,
            'server_ip': server_ip,
            'successful_modules': execution_stats['successful_modules'],
            'failed_modules': execution_stats['failed_modules'],
            'business_metrics': execution_stats.get('business_metrics', {})
        }
        
        # Enviar notificação Discord
        if discord_webhook:
            logger.info("📱 Enviando notificação Discord...")
            discord_success = send_discord_notification(discord_webhook, execution_summary)
            if discord_success:
                logger.info("✅ Notificação Discord enviada!")
            else:
                logger.warning("⚠️  Falha ao enviar notificação Discord")
        
    except Exception as e:
        logger.error(f"❌ Erro ao preparar notificação Discord: {e}")
        send_cloudwatch_metric('DiscordPreparationFailed', 1)
    
    if success_rate >= 80:
        logger.info("🎉 EXECUÇÃO CONCLUÍDA COM SUCESSO!")
        send_cloudwatch_metric('ExecutionCompleted', 1)
        return True
    else:
        logger.warning("⚠️  Execução concluída com problemas")
        send_cloudwatch_metric('ExecutionPartialSuccess', 1)
        return False

def calculate_business_metrics(data, query_type, date_filter=None):
    """Calcula métricas de negócio dos dados processados"""
    if not data:
        return {}
    
    metrics = {}
    
    try:
        if query_type == "Analitico":
            # Análise de vendas
            total_vendas = 0
            total_desconto = 0
            total_custo = 0
            produtos_vendidos = set()
            
            for record in data:
                if len(record) >= 26:  # Verificar se tem todas as colunas
                    # Coluna V (índice 21) = valorfinal, U (índice 20) = desconto, W (índice 22) = custo
                    valor_final = parse_monetary_for_calc(record[21])  # valorfinal
                    desconto = parse_monetary_for_calc(record[20])     # desconto
                    custo = parse_monetary_for_calc(record[22])        # custo
                    produto = record[16]  # prd_desc (índice 16)
                    
                    total_vendas += valor_final
                    total_desconto += desconto
                    total_custo += custo
                    if produto:
                        produtos_vendidos.add(produto)
            
            metrics = {
                'total_vendas': f"R$ {total_vendas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'total_desconto': f"R$ {total_desconto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'total_custo': f"R$ {total_custo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'margem_bruta': f"R$ {(total_vendas - total_custo):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'produtos_diferentes': len(produtos_vendidos),
                'ticket_medio': f"R$ {(total_vendas / len(data) if len(data) > 0 else 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            }
            
        elif query_type == "NF":
            # Análise de notas fiscais
            total_autorizado = 0
            total_cancelado = 0
            nfs_autorizadas = 0
            nfs_canceladas = 0
            
            for record in data:
                if len(record) >= 18:  # Verificar se tem todas as colunas
                    valor_autorizado = parse_monetary_for_calc(record[12])  # M = valor_autorizado
                    valor_cancelado = parse_monetary_for_calc(record[17])   # R = valor_cancelado
                    autorizada = record[10]  # K = autorizada
                    cancelada = record[9]    # J = cancelada
                    
                    total_autorizado += valor_autorizado
                    total_cancelado += valor_cancelado
                    
                    if str(autorizada).lower() in ['true', '1', 'sim', 's']:
                        nfs_autorizadas += 1
                    if str(cancelada).lower() in ['true', '1', 'sim', 's']:
                        nfs_canceladas += 1
            
            metrics = {
                'total_autorizado': f"R$ {total_autorizado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'total_cancelado': f"R$ {total_cancelado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'nfs_autorizadas': nfs_autorizadas,
                'nfs_canceladas': nfs_canceladas,
                'taxa_cancelamento': f"{(nfs_canceladas / len(data) * 100 if len(data) > 0 else 0):.1f}%"
            }
            
        elif query_type == "Pagamentos":
            # Análise de pagamentos
            total_pagamentos = 0
            meios_pagamento = {}
            tipos_pagamento = {}
            
            for record in data:
                if len(record) >= 26:  # Verificar se tem todas as colunas
                    valor = parse_monetary_for_calc(record[13])  # N = valor
                    meio = record[18]   # S = meio
                    tipo = record[17]   # R = tipo
                    
                    total_pagamentos += valor
                    
                    # Contar meios de pagamento
                    if meio:
                        meios_pagamento[meio] = meios_pagamento.get(meio, 0) + valor
                    
                    # Contar tipos de pagamento
                    if tipo:
                        tipos_pagamento[tipo] = tipos_pagamento.get(tipo, 0) + 1
            
            # Encontrar meio de pagamento mais usado
            meio_principal = max(meios_pagamento.items(), key=lambda x: x[1]) if meios_pagamento else ("N/A", 0)
            
            metrics = {
                'total_pagamentos': f"R$ {total_pagamentos:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'transacoes': len(data),
                'ticket_medio': f"R$ {(total_pagamentos / len(data) if len(data) > 0 else 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'meio_principal': f"{meio_principal[0]} (R$ {meio_principal[1]:,.2f})".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'meios_diferentes': len(meios_pagamento)
            }
            
        elif query_type == "Periodo":
            # Análise de períodos
            total_faturamento = 0
            total_pessoas = 0
            total_itens = 0
            mesas_atendidas = set()
            
            for record in data:
                if len(record) >= 24:  # Verificar se tem todas as colunas
                    vr_pagamentos = parse_monetary_for_calc(record[11])  # L = vr_pagamentos (índice 11)
                    pessoas = int(record[9]) if str(record[9]).isdigit() else 0  # J = pessoas (índice 9)
                    qtd_itens = int(record[10]) if str(record[10]).isdigit() else 0  # K = qtd_itens (índice 10)
                    vd = record[2]  # C = vd (número da mesa/comanda)
                    
                    total_faturamento += vr_pagamentos
                    total_pessoas += pessoas
                    total_itens += qtd_itens
                    if vd:
                        mesas_atendidas.add(vd)
            
            metrics = {
                'faturamento_total': f"R$ {total_faturamento:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'pessoas_atendidas': total_pessoas,
                'itens_vendidos': total_itens,
                'mesas_diferentes': len(mesas_atendidas),
                'faturamento_por_pessoa': f"R$ {(total_faturamento / total_pessoas if total_pessoas > 0 else 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            }
            
        elif query_type == "Tempo":
            # Análise de tempos de produção
            produtos_analisados = set()
            grupos_analisados = set()
            
            for record in data:
                if len(record) >= 35:  # Verificar se tem todas as colunas
                    produto = record[3]  # D = prd_desc
                    grupo = record[2]    # C = grp_desc
                    
                    if produto:
                        produtos_analisados.add(produto)
                    if grupo:
                        grupos_analisados.add(grupo)
            
            metrics = {
                'produtos_analisados': len(produtos_analisados),
                'grupos_analisados': len(grupos_analisados),
                'registros_tempo': len(data)
            }
            
        elif query_type == "FatPorHora":
            # Análise de faturamento por hora
            faturamento_por_hora = {}
            total_faturamento = 0
            
            for record in data:
                if len(record) >= 8:  # Verificar se tem todas as colunas
                    hora = record[5]    # F = hora
                    valor = parse_monetary_for_calc(record[7])  # H = valor
                    
                    total_faturamento += valor
                    if hora:
                        faturamento_por_hora[hora] = faturamento_por_hora.get(hora, 0) + valor
            
            # Encontrar melhor hora
            melhor_hora = max(faturamento_por_hora.items(), key=lambda x: x[1]) if faturamento_por_hora else ("N/A", 0)
            
            metrics = {
                'faturamento_total': f"R$ {total_faturamento:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'horas_analisadas': len(faturamento_por_hora),
                'melhor_hora': f"{melhor_hora[0]} (R$ {melhor_hora[1]:,.2f})".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'media_por_hora': f"R$ {(total_faturamento / len(faturamento_por_hora) if len(faturamento_por_hora) > 0 else 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            }
    
    except Exception as e:
        logger.error(f"❌ Erro ao calcular métricas para {query_type}: {e}")
        metrics = {'erro': f"Erro no cálculo: {str(e)[:50]}"}
    
    return metrics

def parse_monetary_for_calc(value):
    """Converte valor monetário para float para cálculos"""
    if value is None or value == "" or value == "None":
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Remover formatação brasileira
        clean_value = value.replace('R$', '').replace(' ', '').strip()
        if clean_value == "":
            return 0.0
        
        # Se tem vírgula como decimal
        if ',' in clean_value:
            # Se tem ponto como separador de milhar
            if '.' in clean_value and clean_value.rindex('.') < clean_value.rindex(','):
                clean_value = clean_value.replace('.', '').replace(',', '.')
            else:
                clean_value = clean_value.replace(',', '.')
        
        try:
            return float(clean_value)
        except ValueError:
            return 0.0
    
    return 0.0

def format_business_metrics_for_discord(execution_summary):
    """Formata as métricas de negócio para inclusão na notificação Discord"""
    business_metrics = execution_summary.get('business_metrics')
    if not business_metrics:
        return ""
    
    metrics_text = ""
    
    for module_name, metrics in business_metrics.items():
        if not metrics:
            continue
            
        metrics_text += f"**{module_name}:**\n"
        
        for key, value in metrics.items():
            # Formatar nomes das métricas
            key_formatted = key.replace('_', ' ').title()
            metrics_text += f"• {key_formatted}: {value}\n"
        
        metrics_text += "\n"
    
    return metrics_text.strip()

def format_date_brazilian(date_str):
    """Converte data do formato ISO (YYYY-MM-DD) para formato brasileiro (DD/MM/AAAA)"""
    if not date_str:
        return ""
    
    try:
        # Remover aspas simples se existir
        if isinstance(date_str, str) and date_str.startswith("'"):
            date_str = date_str[1:]
        
        # Se contém 'T', pegar apenas a parte da data
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
        
        # Verificar se já está no formato brasileiro
        if len(date_str) == 10 and date_str[2] == '/' and date_str[5] == '/':
            return date_str  # Já está no formato DD/MM/AAAA
        
        # Se está no formato ISO (YYYY-MM-DD)
        if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
            year, month, day = date_str.split('-')
            return f"{day}/{month}/{year}"
        
        # Se for um objeto datetime
        if hasattr(date_str, 'strftime'):
            return date_str.strftime("%d/%m/%Y")
        
        return date_str  # Retornar como está se não conseguir converter
        
    except Exception as e:
        logger.error(f"Erro ao formatar data '{date_str}': {e}")
        return date_str  # Retornar original em caso de erro

# DISABLED - OLD FUNCTION
# FUNÇÃO DESABILITADA
def monitor_spreadsheet_usage(client, spreadsheet_name):
    return {"total_cells": 0, "usage_percent": 0.0, "limit": 10000000}

def monitor_spreadsheet_usage_OLD(client, spreadsheet_name):
    """Monitora o uso de células em todas as abas da planilha"""
    try:
        spreadsheet = client.open(spreadsheet_name)
        total_cells = 0
        usage_report = []
        
        logger.info("📊 Monitorando uso de células...")
        
        for worksheet in spreadsheet.worksheets():
            rows = worksheet.row_count
            cols = worksheet.col_count
            cells = rows * cols
            total_cells += cells
            
            # Verificar quantas células têm dados
            try:
                all_values = worksheet.get_all_values()
                used_cells = sum(1 for row in all_values for cell in row if cell.strip())
                usage_percent = (used_cells / cells * 100) if cells > 0 else 0
                
                usage_report.append({
                    'name': worksheet.title,
                    'dimensions': f"{rows}x{cols}",
                    'total_cells': cells,
                    'used_cells': used_cells,
                    'usage_percent': usage_percent
                })
                
                logger.info(f"  📋 {worksheet.title}: {rows}x{cols} = {cells:,} células ({used_cells:,} usadas - {usage_percent:.1f}%)")
                
            except Exception as e:
                logger.warning(f"  ⚠️ Erro ao verificar dados em {worksheet.title}: {e}")
                usage_report.append({
                    'name': worksheet.title,
                    'dimensions': f"{rows}x{cols}",
                    'total_cells': cells,
                    'used_cells': 0,
                    'usage_percent': 0
                })
        
        logger.info(f"📊 Total de células: {total_cells:,}")
        
        # Verificar se está próximo do limite
        limit = 10000000
        usage_percent = (total_cells / limit) * 100
        
        if usage_percent > 90:
            logger.warning(f"⚠️ ATENÇÃO: Uso de células alto ({usage_percent:.1f}% do limite)")
        elif usage_percent > 75:
            logger.info(f"📈 Uso de células moderado ({usage_percent:.1f}% do limite)")
        else:
            logger.info(f"✅ Uso de células normal ({usage_percent:.1f}% do limite)")
        
        # Enviar métrica para CloudWatch
        send_cloudwatch_metric('TotalCellsUsed', total_cells)
        send_cloudwatch_metric('CellUsagePercent', usage_percent)
        
        return {
            'total_cells': total_cells,
            'usage_percent': usage_percent,
            'worksheets': usage_report,
            'limit': limit
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao monitorar uso da planilha: {e}")
        return None

def get_brazilian_time():
    """Obter horário atual no fuso brasileiro (UTC-3)"""
    try:
        if ZoneInfo:
            # Python 3.9+
            utc_time = datetime.now(ZoneInfo('UTC'))
            br_time = utc_time.astimezone(ZoneInfo('America/Sao_Paulo'))
        elif pytz:
            # Python < 3.9 com pytz
            utc_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
            br_tz = pytz.timezone('America/Sao_Paulo')
            br_time = utc_time.astimezone(br_tz)
        else:
            # Fallback: subtrair 3 horas manualmente
            utc_time = datetime.utcnow()
            br_time = utc_time - timedelta(hours=3)
        
        return br_time
    except Exception as e:
        logger.error(f"❌ Erro ao obter horário brasileiro: {e}")
        # Fallback: subtrair 3 horas do UTC
        return datetime.utcnow() - timedelta(hours=3)

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        send_cloudwatch_metric('CriticalError', 1)
        sys.exit(1)
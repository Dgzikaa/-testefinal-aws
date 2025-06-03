#!/usr/bin/env python3
"""
Script de teste para debugar a função process_visao_competencia
"""
import os
import time
import logging
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
import pyotp

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações (mesmas do testefinal.py)
CONTA_AZUL_EMAIL = "rodrigo@grupomenosemais.com.br"
CONTA_AZUL_SENHA = "Ca12345@"
SECRET_2FA = "PKB7MTXCP5M3Y54C6KGTZFMXONAGOLQDUKGDN3LF5U4XAXNULP4A"
DOWNLOAD_PATH = os.path.join(os.getcwd(), "downloads")  # Pasta local para testes
EXPORT_FILE_NAME = "visao_competencia.xls"

# Criar pasta de downloads se não existir
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)
    logger.info(f"📁 Pasta de downloads criada: {DOWNLOAD_PATH}")

# Lista de seletores para pop-ups
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

def test_visao_competencia():
    """Função de teste para debugar a Visão de Competência"""
    logger.info("🚀 INICIANDO TESTE DA VISÃO DE COMPETÊNCIA")
    logger.info("=" * 50)
    
    # Configurar Chrome para Windows local (não headless para debug)
    options = webdriver.ChromeOptions()
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
    
    logger.info(f"📁 Pasta de download configurada: {DOWNLOAD_PATH}")
    
    driver = None
    try:
        logger.info("🌐 Iniciando navegador Chrome...")
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 30)
        
        # 1) Acessar a página de login
        logger.info("🔐 Acessando página de Login da Conta Azul...")
        driver.get("https://login.contaazul.com/#/")
        time.sleep(3)
        
        # Verificar e fechar pop-ups antes do login
        check_and_close_popups(driver, wait)
        
        # Debug: capturar screenshot da página de login
        screenshot_path = os.path.join(DOWNLOAD_PATH, "login_page.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"📸 Screenshot da página de login salvo: {screenshot_path}")
        
        logger.info("📝 Preenchendo credenciais...")
        
        # Encontrar e preencher email
        try:
            email_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='email']")))
            email_input.clear()
            email_input.send_keys(CONTA_AZUL_EMAIL)
            logger.info(f"✅ Email preenchido: {CONTA_AZUL_EMAIL}")
        except TimeoutException:
            logger.error("❌ Campo de email não encontrado")
            return None
        
        # Encontrar e preencher senha
        try:
            password_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
            password_input.clear()
            password_input.send_keys(CONTA_AZUL_SENHA)
            logger.info("✅ Senha preenchida")
        except TimeoutException:
            logger.error("❌ Campo de senha não encontrado")
            return None
        
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
            return None
        
        time.sleep(5)
        
        # 2) Realizar o MFA (2FA)
        logger.info("🔒 Processando 2FA...")
        totp = pyotp.TOTP(SECRET_2FA)
        codigo_2fa = totp.now()
        logger.info(f"🔑 Código 2FA gerado: {codigo_2fa}")
        
        # Verificar pop-ups novamente
        check_and_close_popups(driver, wait)
        
        # Capturar screenshot da página de 2FA
        screenshot_path = os.path.join(DOWNLOAD_PATH, "mfa_page.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"📸 Screenshot da página de 2FA salvo: {screenshot_path}")
        
        try:
            mfa_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' and @maxlength='6']")))
            mfa_input.clear()
            mfa_input.send_keys(str(codigo_2fa))
            logger.info("✅ Código 2FA inserido")
        except TimeoutException:
            logger.error("❌ Campo de 2FA não encontrado")
            return None
        
        # Verificar pop-ups novamente
        check_and_close_popups(driver, wait)
        
        try:
            botao_mfa = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
                "button.ds-loader-button__button.ds-button.ds-button-primary.ds-button-md.ds-u-width--full")))
            botao_mfa.click()
            logger.info("✅ Botão de 2FA clicado")
        except TimeoutException:
            logger.error("❌ Botão de 2FA não encontrado")
            return None
        
        logger.info("✅ Login + MFA concluídos com sucesso.")
        time.sleep(5)
        
        # Verificar pop-ups após login
        check_and_close_popups(driver, wait)
        
        # Capturar screenshot após login
        screenshot_path = os.path.join(DOWNLOAD_PATH, "after_login.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"📸 Screenshot após login salvo: {screenshot_path}")
        
        # 3) Acessar a Visão de Competência
        logger.info("📊 Acessando Visão de Competência...")
        driver.get("https://app.contaazul.com/#/ca/financeiro/competencia")
        time.sleep(10)  # Aguardar carregamento da página
        
        # Verificar pop-ups após navegação
        check_and_close_popups(driver, wait)
        
        # Capturar screenshot da página de competência
        screenshot_path = os.path.join(DOWNLOAD_PATH, "competencia_page.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"📸 Screenshot da página de competência salvo: {screenshot_path}")
        
        # DEBUG: Listar elementos visíveis na página
        logger.info("🔍 Analisando elementos da página...")
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"🔘 Encontrados {len(buttons)} botões na página")
            
            for i, button in enumerate(buttons[:10]):  # Mostrar apenas os primeiros 10
                try:
                    text = button.text.strip()
                    if text:
                        logger.info(f"  Botão {i+1}: '{text}'")
                except:
                    pass
                    
            # Procurar especificamente por botões de exportação
            export_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Exportar') or contains(text(), 'Export') or contains(@title, 'Export')]")
            logger.info(f"📤 Encontrados {len(export_buttons)} botões de exportação")
            
        except Exception as e:
            logger.error(f"❌ Erro ao analisar elementos: {e}")
        
        # Tentar diferentes estratégias para encontrar o botão de exportação
        export_success = False
        
        # Estratégia 1: XPath original
        try:
            logger.info("📤 Tentativa 1: XPath original...")
            exportar_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/caf-application-layout/div/caf-application/div/div[2]/div[2]/div/main/div/div[2]/div/section/div[2]/div/nav/div/div/div/div[2]/span[1]/button"))
            )
            driver.execute_script("arguments[0].click();", exportar_btn)
            logger.info("✅ Estratégia 1 funcionou!")
            export_success = True
        except TimeoutException:
            logger.warning("⚠️ Estratégia 1 falhou")
        
        # Estratégia 2: Procurar por texto "Exportar"
        if not export_success:
            try:
                logger.info("📤 Tentativa 2: Procurar por texto 'Exportar'...")
                exportar_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Exportar')]"))
                )
                driver.execute_script("arguments[0].click();", exportar_btn)
                logger.info("✅ Estratégia 2 funcionou!")
                export_success = True
            except TimeoutException:
                logger.warning("⚠️ Estratégia 2 falhou")
        
        # Estratégia 3: Procurar por ícones de download
        if not export_success:
            try:
                logger.info("📤 Tentativa 3: Procurar por ícones de download...")
                exportar_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'download') or contains(@title, 'download')]"))
                )
                driver.execute_script("arguments[0].click();", exportar_btn)
                logger.info("✅ Estratégia 3 funcionou!")
                export_success = True
            except TimeoutException:
                logger.warning("⚠️ Estratégia 3 falhou")
        
        if not export_success:
            logger.error("❌ Nenhuma estratégia de exportação funcionou")
            logger.info("📄 Salvando HTML da página para análise...")
            html_path = os.path.join(DOWNLOAD_PATH, "competencia_page.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            logger.info(f"💾 HTML salvo em: {html_path}")
            return None
        
        # Se chegou aqui, o botão foi clicado
        logger.info("⬇️ Aguardando o download do arquivo...")
        time.sleep(20)
        
        # Verificar se o arquivo foi baixado
        file_path = os.path.join(DOWNLOAD_PATH, EXPORT_FILE_NAME)
        if os.path.exists(file_path):
            logger.info("✅ Arquivo exportado encontrado!")
            logger.info(f"📁 Caminho: {file_path}")
            logger.info(f"📊 Tamanho: {os.path.getsize(file_path)} bytes")
            
            # Tentar ler o arquivo
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                df = df.fillna("")  # Substitui valores NaN por string vazia
                
                logger.info(f"📊 DataFrame shape: {df.shape}")
                logger.info(f"📋 DataFrame columns: {df.columns.tolist()}")
                
                if not df.empty:
                    logger.info("📄 Primeiras 3 linhas:")
                    logger.info(df.head(3).to_string())
                
                # Converter para formato compatível
                data = [df.columns.tolist()] + df.values.tolist()
                
                logger.info(f"✅ Dados processados: {len(data)} linhas (incluindo cabeçalho)")
                return data
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar arquivo: {e}")
                return None
        else:
            logger.error("❌ Arquivo exportado não encontrado.")
            logger.info("📁 Arquivos disponíveis na pasta de download:")
            for file in os.listdir(DOWNLOAD_PATH):
                logger.info(f"  - {file}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro durante processamento: {e}")
        return None
    finally:
        if driver:
            logger.info("🚪 Fechando navegador...")
            time.sleep(3)  # Aguardar um pouco antes de fechar
            driver.quit()

if __name__ == "__main__":
    result = test_visao_competencia()
    if result:
        print(f"\n🎉 SUCESSO! {len(result)} linhas de dados obtidas.")
    else:
        print("\n❌ FALHA no teste da Visão de Competência.") 
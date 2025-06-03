#!/usr/bin/env python3
"""
Script de teste ESPECÍFICO para configurar o filtro "Todo o período"
na Visão de Competência do Conta Azul - VERSÃO RÁPIDA
"""
import os
import time
import logging
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import pyotp

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
CONTA_AZUL_EMAIL = "rodrigo@grupomenosemais.com.br"
CONTA_AZUL_SENHA = "Ca12345@"
SECRET_2FA = "PKB7MTXCP5M3Y54C6KGTZFMXONAGOLQDUKGDN3LF5U4XAXNULP4A"
DOWNLOAD_PATH = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

def take_screenshot(driver, filename):
    """Capturar screenshot para debug"""
    try:
        screenshot_path = os.path.join(DOWNLOAD_PATH, f"{filename}.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"📸 Screenshot salvo: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        logger.error(f"❌ Erro ao capturar screenshot: {e}")
        return None

def test_period_filter():
    """Testar especificamente o filtro de período - VERSÃO RÁPIDA"""
    
    # Configurar Chrome
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # Remover headless para debug
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    prefs = {
        "download.default_directory": DOWNLOAD_PATH,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 10)  # Reduzir timeout para 10s
        
        # 1) Login
        logger.info("🔐 Fazendo login...")
        driver.get("https://login.contaazul.com/#/")
        time.sleep(1)  # Reduzir para 1s
        
        # Email
        email_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='email']")))
        email_input.send_keys(CONTA_AZUL_EMAIL)
        
        # Senha
        password_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
        password_input.send_keys(CONTA_AZUL_SENHA)
        
        # Login
        botao_login = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
            "button.ds-loader-button__button.ds-button.ds-button-primary.ds-button-md.ds-u-width--full")))
        botao_login.click()
        time.sleep(1)  # Reduzir para 1s
        
        # 2FA
        logger.info("🔒 Inserindo 2FA...")
        totp = pyotp.TOTP(SECRET_2FA)
        codigo_2fa = totp.now()
        
        mfa_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' and @maxlength='6']")))
        mfa_input.send_keys(str(codigo_2fa))
        time.sleep(5)  # Aumentar de 2 para 5 segundos após inserir o código 2FA
        
        botao_mfa = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
            "button.ds-loader-button__button.ds-button.ds-button-primary.ds-button-md.ds-u-width--full")))
        botao_mfa.click()
        time.sleep(5)  # Aumentar de 2 para 5 segundos após clicar no botão 2FA
        
        # 2) Navegar para Visão de Competência
        logger.info("📊 Acessando Visão de Competência...")
        driver.get("https://app.contaazul.com/#/ca/financeiro/competencia")
        time.sleep(5)  # Aumentar para 5s para garantir carregamento completo da página
        
        # Screenshot inicial
        take_screenshot(driver, "01_pagina_inicial")
        
        # 3) FOCO TOTAL NO FILTRO DE PERÍODO
        logger.info("🔍 PROCURANDO FILTRO DE PERÍODO...")
        
        # Estratégia 1: Procurar por texto que indique filtro de período
        logger.info("📅 Estratégia 1: Procurando por texto relacionado a período...")
        
        period_text_selectors = [
            "//*[contains(text(), 'Período')]",
            "//*[contains(text(), 'Data')]", 
            "//*[contains(text(), 'Filtro')]",
            "//*[contains(text(), 'Competência')]",
            "//*[contains(text(), 'Mês')]",
            "//*[contains(text(), 'Ano')]"
        ]
        
        for i, selector in enumerate(period_text_selectors):
            try:
                elements = driver.find_elements(By.XPATH, selector)
                logger.info(f"  📝 Selector {i+1}: Encontrados {len(elements)} elementos com '{selector}'")
                for j, element in enumerate(elements[:3]):  # Apenas primeiros 3
                    try:
                        text = element.text.strip()
                        if text:
                            logger.info(f"    📋 Elemento {j+1}: '{text}' - Tag: {element.tag_name}")
                    except:
                        pass
            except Exception as e:
                logger.debug(f"    ⚠️ Erro no selector {i+1}: {e}")
        
        # Screenshot após busca inicial
        take_screenshot(driver, "02_busca_inicial")
        
        # Estratégia 2: Procurar dropdowns, selects e botões
        logger.info("📅 Estratégia 2: Procurando elementos interativos...")
        
        interactive_selectors = [
            "//select",
            "//button[contains(@class, 'dropdown')]",
            "//div[contains(@class, 'dropdown')]",
            "//div[contains(@class, 'select')]",
            "//button[contains(@class, 'filter')]",
            "//div[contains(@class, 'filter')]",
            "//button[contains(@class, 'date')]",
            "//div[contains(@class, 'date')]"
        ]
        
        interactive_elements = []
        for i, selector in enumerate(interactive_selectors):
            try:
                elements = driver.find_elements(By.XPATH, selector)
                logger.info(f"  🎛️  Selector {i+1}: {len(elements)} elementos '{selector}'")
                for element in elements:
                    try:
                        # Verificar se está visível
                        if element.is_displayed():
                            interactive_elements.append(element)
                            logger.info(f"    ✅ Elemento visível: {element.tag_name} - Classes: {element.get_attribute('class')}")
                    except:
                        pass
            except Exception as e:
                logger.debug(f"    ⚠️ Erro: {e}")
        
        logger.info(f"📋 Total de elementos interativos encontrados: {len(interactive_elements)}")
        
        # Screenshot após busca de elementos
        take_screenshot(driver, "03_elementos_encontrados")
        
        # Estratégia 3: Tentar interagir com cada elemento potencial
        logger.info("📅 Estratégia 3: Testando interação com elementos...")
        
        filter_found = False
        
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
                
                # NÃO fazer scroll - manter posição atual
                # driver.execute_script("arguments[0].scrollIntoView(true);", period_dropdown)
                
                # Clicar no dropdown de período
                driver.execute_script("arguments[0].click();", period_dropdown)
                time.sleep(2)  # Aguardar abertura do dropdown
                
                # Screenshot após clicar no dropdown correto
                take_screenshot(driver, "04_dropdown_periodo_correto")
                
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
                                
                                # AGUARDAR TEMPO ESTENDIDO para carregamento completo dos dados históricos
                                logger.info("✅ FILTRO CONFIGURADO! Aguardando carregamento completo...")
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
                                                logger.info(f"   ⏳ Ainda carregando... (indicador encontrado)")
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
                                        logger.info(f"⚠️ Poucos dados detectados: ~{total_rows} linhas na tabela")
                                        
                                except Exception as e:
                                    logger.debug(f"Erro ao verificar quantidade de dados: {e}")
                                
                                # Screenshot após seleção e carregamento
                                take_screenshot(driver, f"05_opcao_selecionada_{option.text.replace(' ', '_')}")
                                
                                option_found = True
                                filter_found = True
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
        if not filter_found:
            logger.info("🔄 Fallback: Usando método original de busca...")
            for i, element in enumerate(interactive_elements[:10]):  # Testar até 10 elementos
                try:
                    logger.info(f"  🔍 Testando elemento {i+1}/{min(10, len(interactive_elements))}...")
                    
                    # Scroll até o elemento
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(0.5)  # Reduzir para 0.5s
                    
                    # Tentar clicar
                    driver.execute_script("arguments[0].click();", element)
                    time.sleep(1)  # Reduzir para 1s
                    
                    # Screenshot após clique
                    take_screenshot(driver, f"04_teste_elemento_{i+1}")
                    
                    # Procurar opções que apareceram
                    option_selectors = [
                        "//*[contains(text(), 'Todo')]",
                        "//*[contains(text(), 'Todos')]", 
                        "//*[contains(text(), 'All')]",
                        "//*[contains(text(), 'Completo')]",
                        "//*[contains(text(), 'Período completo')]",
                        "//*[contains(text(), 'Personalizado')]",
                        "//*[contains(text(), 'Custom')]"
                    ]
                    
                    options_found = []
                    for selector in option_selectors:
                        try:
                            options = driver.find_elements(By.XPATH, selector)
                            for option in options:
                                if option.is_displayed():
                                    options_found.append((option, option.text.strip()))
                        except:
                            pass
                    
                    if options_found:
                        logger.info(f"    ✅ Encontradas {len(options_found)} opções após clicar:")
                        for j, (option, text) in enumerate(options_found):
                            logger.info(f"      📋 Opção {j+1}: '{text}'")
                            
                            # Se encontrou "Todo", tentar clicar
                            if any(word in text.lower() for word in ['todo', 'todos', 'all', 'completo']):
                                try:
                                    logger.info(f"      🎯 TENTANDO clicar em: '{text}'")
                                    driver.execute_script("arguments[0].click();", option)
                                    
                                    # AGUARDAR TEMPO ESTENDIDO para carregamento completo dos dados históricos
                                    logger.info("      ✅ FILTRO CONFIGURADO! Aguardando carregamento completo...")
                                    logger.info("         🕐 Fase 1: Aguardando 10 segundos iniciais...")
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
                                        logger.info(f"         🕐 Fase 2: Ciclo {cycle+1}/{max_wait_cycles} - Verificando carregamento...")
                                        
                                        still_loading = False
                                        for indicator in loading_indicators:
                                            try:
                                                loading_elements = driver.find_elements(By.XPATH, indicator)
                                                if any(el.is_displayed() for el in loading_elements):
                                                    still_loading = True
                                                    logger.info(f"         ⏳ Ainda carregando... (indicador encontrado)")
                                                    break
                                            except:
                                                continue
                                        
                                        if not still_loading:
                                            logger.info(f"         ✅ Carregamento aparentemente concluído no ciclo {cycle+1}")
                                            break
                                        
                                        time.sleep(5)  # Aguardar 5 segundos entre verificações
                                    
                                    # Aguardar mais 10 segundos de segurança após carregamento
                                    logger.info("         🕐 Fase 3: Aguardando 10 segundos finais de segurança...")
                                    time.sleep(10)
                                    
                                    # Total: 10s inicial + até 30s verificando + 10s final = até 50 segundos
                                    logger.info("      ✅ Tempo de carregamento estendido concluído!")
                                    
                                    # IMPORTANTE: Rolar para o topo para garantir que o botão de exportação esteja visível
                                    logger.info("      📏 Rolando para o topo para garantir visibilidade do botão de exportação...")
                                    driver.execute_script("window.scrollTo(0, 0);")
                                    time.sleep(2)  # Aguardar scroll
                                    
                                    # Verificar se a página tem mais dados agora
                                    try:
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
                                            logger.info(f"      ✅ Mais dados detectados: ~{total_rows} linhas na tabela")
                                        else:
                                            logger.info(f"      ⚠️ Poucos dados detectados: ~{total_rows} linhas na tabela")
                                            
                                    except Exception as e:
                                        logger.debug(f"Erro ao verificar quantidade de dados: {e}")
                                    
                                    # Screenshot após seleção e carregamento
                                    take_screenshot(driver, f"05_opcao_selecionada_{text.replace(' ', '_')}")
                                    
                                    filter_found = True
                                    break
                                except Exception as e:
                                    logger.warning(f"      ⚠️ Erro ao clicar na opção: {e}")
                        
                        if filter_found:
                            break
                    
                    # Se não encontrou opções, tentar ESC para fechar
                    driver.execute_script("document.activeElement.blur();")
                    time.sleep(0.5)  # Reduzir para 0.5s
                    
                except Exception as e:
                    logger.debug(f"    ⚠️ Erro ao testar elemento {i+1}: {e}")
        
        # Screenshot final após tentativas
        take_screenshot(driver, "06_final_tentativas")
        
        # 4) Tentar exportar mesmo sem conseguir configurar filtro
        logger.info("📤 Tentando exportar dados...")
        
        export_button = None
        export_selectors = [
            "/html/body/caf-application-layout/div/caf-application/div/div[2]/div[2]/div/main/div/div[2]/div/section/div[2]/div/nav/div/div/div/div[2]/span[1]/button",
            "//button[contains(text(), 'Exportar')]",
            "//button[contains(text(), 'Export')]"
        ]
        
        for selector in export_selectors:
            try:
                export_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, selector)))
                logger.info(f"✅ Botão de exportação encontrado!")
                break
            except TimeoutException:
                continue
        
        if export_button:
            driver.execute_script("arguments[0].click();", export_button)
            logger.info("📤 Clicado no botão de exportação!")
            time.sleep(5)  # Aguardar download - mantém 5s
            
            # Verificar arquivo baixado
            files = [f for f in os.listdir(DOWNLOAD_PATH) if f.endswith('.xls')]
            if files:
                latest_file = max([os.path.join(DOWNLOAD_PATH, f) for f in files], key=os.path.getctime)
                file_size = os.path.getsize(latest_file)
                logger.info(f"✅ Arquivo baixado: {latest_file} ({file_size} bytes)")
                
                # Analisar dados
                try:
                    df = pd.read_excel(latest_file, engine='openpyxl')
                    logger.info(f"📊 DADOS EXTRAÍDOS: {len(df)} registros, {len(df.columns)} colunas")
                    
                    if filter_found:
                        logger.info("🎉 SUCESSO TOTAL: Filtro configurado + dados extraídos!")
                    else:
                        logger.warning(f"⚠️ PARCIAL: {len(df)} registros (esperado: 6000+)")
                        logger.warning("❌ Filtro 'Todo o período' NÃO foi configurado")
                    
                    return len(df), filter_found
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao analisar arquivo: {e}")
            else:
                logger.error("❌ Nenhum arquivo foi baixado")
        else:
            logger.error("❌ Botão de exportação não encontrado")
        
        return 0, False
        
    except Exception as e:
        logger.error(f"❌ Erro durante teste: {e}")
        return 0, False
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    logger.info("🚀 INICIANDO TESTE RÁPIDO DO FILTRO DE PERÍODO")
    records, filter_success = test_period_filter()
    
    if filter_success and records > 5000:
        logger.info("🎉 TESTE BEM-SUCEDIDO: Filtro funcionou e dados completos extraídos!")
    elif records > 0:
        logger.warning(f"⚠️ TESTE PARCIAL: {records} registros extraídos (filtro não configurado)")
    else:
        logger.error("❌ TESTE FALHOU: Nenhum dado extraído") 
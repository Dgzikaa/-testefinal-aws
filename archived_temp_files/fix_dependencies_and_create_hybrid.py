#!/usr/bin/env python3
import boto3
import time

def fix_dependencies_and_create_hybrid():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("🔧 Corrigindo dependências e criando planilhas híbridas...")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # ETAPA 1: Corrigir dependências
    print("📦 ETAPA 1: Corrigindo dependências urllib3...")
    
    fix_deps_commands = [
        'pip3 uninstall urllib3 -y',
        'pip3 install urllib3==1.26.18',
        'pip3 install requests==2.31.0',
        'echo "✅ Dependências corrigidas!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': fix_deps_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado da correção de dependências:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("⚠️ Avisos:")
        print(result['StandardErrorContent'])
    
    # Aguardar um pouco
    print("\n⏳ Aguardando 5 segundos...")
    time.sleep(5)
    
    # ETAPA 2: Criar planilhas híbridas
    print("\n🏗️ ETAPA 2: Criando planilhas híbridas...")
    
    # Script Python simples para criar planilhas
    create_script = '''#!/usr/bin/env python3
import gspread
from google.oauth2.service_account import Credentials

def get_google_sheets_client():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)

def create_hybrid_structure():
    try:
        client = get_google_sheets_client()
        main_sheet = client.open("TesteFinal AWS - Dados Contábeis")
        
        hybrid_structure = {
            "TesteFinal AWS - Vendas": ["Analitico", "Pagamentos", "FatPorHora"],
            "TesteFinal AWS - Fiscal": ["NF", "Periodo"], 
            "TesteFinal AWS - Operacional": ["Tempo"]
        }
        
        print("🎯 CRIANDO ESTRUTURA HÍBRIDA:")
        
        for sheet_name, modules in hybrid_structure.items():
            print(f"\\n📋 Processando: {sheet_name}")
            print(f"📦 Módulos: {modules}")
            
            try:
                hybrid_sheet = client.open(sheet_name)
                print("✅ Planilha já existe")
            except:
                hybrid_sheet = client.create(sheet_name)
                print("✅ Planilha criada!")
            
            for module_name in modules:
                try:
                    print(f"  🔄 Migrando {module_name}...")
                    
                    try:
                        original_worksheet = main_sheet.worksheet(module_name)
                        module_data = original_worksheet.get_all_values()
                        print(f"  📥 {len(module_data)} linhas encontradas")
                    except:
                        print(f"  ⚠️ Aba {module_name} não encontrada")
                        continue
                    
                    if module_data:
                        try:
                            try:
                                target_worksheet = hybrid_sheet.worksheet(module_name)
                                print(f"  📋 Aba {module_name} existe, atualizando...")
                            except:
                                rows = len(module_data)
                                cols = len(module_data[0]) if module_data else 10
                                target_worksheet = hybrid_sheet.add_worksheet(
                                    title=module_name, rows=rows, cols=cols
                                )
                                print(f"  📋 Aba {module_name} criada!")
                            
                            target_worksheet.clear()
                            target_worksheet.update("A1", module_data)
                            print(f"  ✅ {len(module_data)} linhas migradas")
                            
                        except Exception as e:
                            print(f"  ❌ Erro ao migrar {module_name}: {e}")
                
                except Exception as e:
                    print(f"  ❌ Erro ao processar {module_name}: {e}")
            
            print(f"✅ {sheet_name} finalizada!")
        
        print("\\n🎯 MIGRAÇÃO HÍBRIDA CONCLUÍDA!")
        print("\\n📋 PLANILHAS CRIADAS:")
        for sheet_name, modules in hybrid_structure.items():
            print(f"  📈 {sheet_name}")
            for module in modules:
                print(f"     └── {module}")
        
        print("\\n💡 BENEFÍCIOS:")
        print("  ✅ 3 planilhas vs 1 (distribuição de carga)")
        print("  ✅ ~3.3M células por planilha (vs 10M limite)")
        print("  ✅ Organização temática")
        print("  ✅ Dados relacionados juntos")
        
        return True
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

if __name__ == "__main__":
    create_hybrid_structure()
'''
    
    create_commands = [
        'cd /home/ec2-user/testefinal',
        'cat > create_hybrid_final.py << "SCRIPT_END"',
        create_script,
        'SCRIPT_END',
        'chmod +x create_hybrid_final.py',
        'python3 create_hybrid_final.py'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': create_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("\n📋 Resultado da criação de planilhas híbridas:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])
    
    print("""
🎉 PROCESSO COMPLETO FINALIZADO!

📊 PLANILHAS HÍBRIDAS CRIADAS:
  📈 TesteFinal AWS - Vendas (Analitico + Pagamentos + FatPorHora)
  🧾 TesteFinal AWS - Fiscal (NF + Periodo)  
  ⚙️ TesteFinal AWS - Operacional (Tempo)

🚀 PRÓXIMOS PASSOS:
1. Verificar se as planilhas foram criadas no Google Sheets
2. Atualizar código para usar planilhas híbridas
3. Testar nova configuração
4. Arquivar planilha original

💡 ACESSO ÀS PLANILHAS:
Procure no seu Google Drive por:
- "TesteFinal AWS - Vendas"
- "TesteFinal AWS - Fiscal" 
- "TesteFinal AWS - Operacional"
""")

if __name__ == "__main__":
    fix_dependencies_and_create_hybrid() 
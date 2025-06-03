#!/usr/bin/env python3
import boto3
import base64

def upload_hybrid_script():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    # Script corrigido para planilhas híbridas
    script_content = '''#!/usr/bin/env python3
import gspread
from google.oauth2.service_account import Credentials

def get_google_sheets_client():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)

def create_hybrid_structure():
    client = get_google_sheets_client()
    main_sheet = client.open("TesteFinal AWS - Dados Contábeis")
    
    hybrid_structure = {
        "TesteFinal AWS - Vendas": ["Analitico", "Pagamentos", "FatPorHora"],
        "TesteFinal AWS - Fiscal": ["NF", "Periodo"],
        "TesteFinal AWS - Operacional": ["Tempo"]
    }
    
    print("🎯 CRIANDO ESTRUTURA HÍBRIDA:")
    
    for sheet_name, modules in hybrid_structure.items():
        try:
            print(f"\\n📋 Processando: {sheet_name}")
            print(f"📦 Módulos: {modules}")
            
            # Criar planilha híbrida
            try:
                hybrid_sheet = client.open(sheet_name)
                print("✅ Planilha já existe")
            except:
                hybrid_sheet = client.create(sheet_name)
                print("✅ Planilha criada!")
            
            # Migrar cada módulo
            for module_name in modules:
                try:
                    print(f"  🔄 Migrando {module_name}...")
                    
                    # Ler dados originais
                    try:
                        original_worksheet = main_sheet.worksheet(module_name)
                        module_data = original_worksheet.get_all_values()
                        print(f"  📥 {len(module_data)} linhas encontradas")
                    except:
                        print(f"  ⚠️ Aba {module_name} não encontrada")
                        continue
                    
                    if module_data:
                        try:
                            # Criar/atualizar aba
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
                            
                            # Migrar dados
                            target_worksheet.clear()
                            target_worksheet.update("A1", module_data)
                            print(f"  ✅ {len(module_data)} linhas migradas")
                            
                        except Exception as e:
                            print(f"  ❌ Erro ao migrar {module_name}: {e}")
                
                except Exception as e:
                    print(f"  ❌ Erro ao processar {module_name}: {e}")
            
            print(f"✅ {sheet_name} finalizada!")
            
        except Exception as e:
            print(f"❌ Erro geral em {sheet_name}: {e}")
    
    print("\\n🎯 MIGRAÇÃO HÍBRIDA CONCLUÍDA!")
    print("\\n📋 PLANILHAS CRIADAS:")
    for sheet_name, modules in hybrid_structure.items():
        print(f"  📈 {sheet_name}")
        for module in modules:
            print(f"     └── {module}")
    
    return True

if __name__ == "__main__":
    create_hybrid_structure()
'''
    
    # Codificar em base64
    script_b64 = base64.b64encode(script_content.encode('utf-8')).decode('ascii')
    
    ssm = boto3.client('ssm', region_name=region)
    
    commands = [
        'cd /home/ec2-user/testefinal',
        f'echo "{script_b64}" | base64 -d > create_hybrid_final.py',
        'chmod +x create_hybrid_final.py',
        'echo "🚀 Executando criação de planilhas híbridas..."',
        'python3 create_hybrid_final.py',
        'echo "✅ Processo concluído!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado da criação de planilhas híbridas:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])

if __name__ == "__main__":
    upload_hybrid_script() 
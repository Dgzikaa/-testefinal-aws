#!/usr/bin/env python3
import boto3
import base64

def create_hybrid_simple():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("🏗️ Criando planilhas híbridas (versão simplificada)...")
    
    # Script Python muito simples
    script_content = '''#!/usr/bin/env python3
import gspread
from google.oauth2.service_account import Credentials

def main():
    print("🔄 Iniciando criação de planilhas híbridas...")
    
    try:
        # Conectar ao Google Sheets
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        client = gspread.authorize(creds)
        
        print("✅ Conectado ao Google Sheets")
        
        # Acessar planilha original
        main_sheet = client.open("TesteFinal AWS - Dados Contábeis")
        print("✅ Planilha original acessada")
        
        # Estrutura híbrida
        hybrid_plans = {
            "TesteFinal AWS - Vendas": ["Analitico", "Pagamentos", "FatPorHora"],
            "TesteFinal AWS - Fiscal": ["NF", "Periodo"], 
            "TesteFinal AWS - Operacional": ["Tempo"]
        }
        
        for plan_name, modules in hybrid_plans.items():
            print(f"\\n📋 Criando: {plan_name}")
            
            # Criar planilha
            try:
                new_sheet = client.open(plan_name)
                print(f"  ✅ Planilha já existe")
            except:
                new_sheet = client.create(plan_name)
                print(f"  ✅ Planilha criada!")
            
            # Migrar módulos
            for module in modules:
                print(f"  🔄 Migrando {module}...")
                try:
                    source = main_sheet.worksheet(module)
                    data = source.get_all_values()
                    
                    if data:
                        try:
                            target = new_sheet.worksheet(module)
                        except:
                            target = new_sheet.add_worksheet(title=module, rows=len(data), cols=len(data[0]))
                        
                        target.clear()
                        target.update("A1", data)
                        print(f"    ✅ {len(data)} linhas migradas")
                    else:
                        print(f"    ⚠️ Sem dados")
                        
                except Exception as e:
                    print(f"    ❌ Erro: {e}")
        
        print("\\n🎉 PLANILHAS HÍBRIDAS CRIADAS COM SUCESSO!")
        print("\\n📊 Acesse no Google Drive:")
        for plan_name in hybrid_plans.keys():
            print(f"  📈 {plan_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

if __name__ == "__main__":
    main()
'''
    
    # Codificar em base64
    script_b64 = base64.b64encode(script_content.encode('utf-8')).decode('ascii')
    
    ssm = boto3.client('ssm', region_name=region)
    
    commands = [
        'cd /home/ec2-user/testefinal',
        f'echo "{script_b64}" | base64 -d > create_hybrid_simple.py',
        'chmod +x create_hybrid_simple.py',
        'echo "🚀 Executando criação simplificada..."',
        'python3 create_hybrid_simple.py'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado da criação:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])

if __name__ == "__main__":
    create_hybrid_simple() 
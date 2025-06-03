#!/usr/bin/env python3
import boto3

def create_separate_spreadsheets():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("📊 Criando planilhas separadas para cada módulo...")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Comandos para criar planilhas separadas
    separate_commands = [
        'cd /home/ec2-user/testefinal',
        
        # Criar script de separação
        'cat > separate_spreadsheets.py << "EOF"',
        '#!/usr/bin/env python3',
        'import gspread',
        'from google.oauth2.service_account import Credentials',
        '',
        'def get_google_sheets_client():',
        '    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]',
        '    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)',
        '    return gspread.authorize(creds)',
        '',
        'def create_separate_sheets():',
        '    client = get_google_sheets_client()',
        '    ',
        '    # Acessar planilha original',
        '    main_sheet = client.open("TesteFinal AWS - Dados Contábeis")',
        '    ',
        '    modules = {',
        '        "Analitico": "TesteFinal AWS - Analitico",',
        '        "NF": "TesteFinal AWS - NF",',
        '        "Periodo": "TesteFinal AWS - Periodo", ',
        '        "Tempo": "TesteFinal AWS - Tempo",',
        '        "Pagamentos": "TesteFinal AWS - Pagamentos",',
        '        "FatPorHora": "TesteFinal AWS - FatPorHora"',
        '    }',
        '    ',
        '    for module_name, new_sheet_name in modules.items():',
        '        try:',
        '            print(f"\\n🔄 Processando {module_name}...")',
        '            ',
        '            # 1. Ler dados da aba original',
        '            try:',
        '                worksheet = main_sheet.worksheet(module_name)',
        '                all_data = worksheet.get_all_values()',
        '                print(f"📥 {len(all_data)} linhas encontradas em {module_name}")',
        '            except:',
        '                print(f"⚠️ Aba {module_name} não encontrada, criando vazia")',
        '                all_data = []',
        '            ',
        '            # 2. Criar nova planilha separada',
        '            try:',
        '                separate_sheet = client.open(new_sheet_name)',
        '                print(f"📋 Planilha {new_sheet_name} já existe")',
        '            except:',
        '                separate_sheet = client.create(new_sheet_name)',
        '                print(f"📋 Planilha {new_sheet_name} criada!")',
        '            ',
        '            # 3. Migrar dados se houver',
        '            if all_data:',
        '                try:',
        '                    # Usar a primeira aba da nova planilha',
        '                    target_worksheet = separate_sheet.get_worksheet(0)',
        '                    target_worksheet.update("A1", all_data)',
        '                    print(f"✅ {len(all_data)} linhas migradas para {new_sheet_name}")',
        '                except Exception as e:',
        '                    print(f"❌ Erro ao migrar dados: {e}")',
        '            ',
        '            # 4. Compartilhar com mesmas permissões',
        '            try:',
        '                # Obter lista de pessoas com acesso à planilha original',
        '                main_permissions = main_sheet.list_permissions()',
        '                for perm in main_permissions:',
        '                    if perm.get("emailAddress"):',
        '                        separate_sheet.share(perm["emailAddress"], perm_type="user", role="writer")',
        '                print(f"🔗 Permissões compartilhadas para {new_sheet_name}")',
        '            except Exception as e:',
        '                print(f"⚠️ Aviso: Não foi possível compartilhar automaticamente: {e}")',
        '            ',
        '        except Exception as e:',
        '            print(f"❌ Erro ao processar {module_name}: {e}")',
        '    ',
        '    print("\\n🎯 MIGRAÇÃO CONCLUÍDA!")',
        '    print("\\n📋 PLANILHAS CRIADAS:")',
        '    for module_name, new_sheet_name in modules.items():',
        '        print(f"  • {new_sheet_name}")',
        '    ',
        '    print("\\n⚠️ PRÓXIMOS PASSOS:")',
        '    print("1. Verificar se todas as planilhas foram criadas")',
        '    print("2. Atualizar código para usar planilhas separadas")',
        '    print("3. Testar nova configuração")',
        '    print("4. Remover planilha original (opcional)")',
        '',
        'if __name__ == "__main__":',
        '    create_separate_sheets()',
        'EOF',
        
        # Executar separação
        'echo "🚀 Executando separação de planilhas..."',
        'python3 separate_spreadsheets.py',
        
        'echo "✅ Separação concluída!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': separate_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado da separação:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])

if __name__ == "__main__":
    create_separate_spreadsheets() 
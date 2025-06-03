#!/usr/bin/env python3
import boto3

def create_hybrid_spreadsheets():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("🗂️ Criando planilhas híbridas por categoria...")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Comandos para criar planilhas híbridas
    hybrid_commands = [
        'cd /home/ec2-user/testefinal',
        
        # Criar script de planilhas híbridas
        'cat > create_hybrid_sheets.py << "EOF"',
        '#!/usr/bin/env python3',
        'import gspread',
        'from google.oauth2.service_account import Credentials',
        '',
        'def get_google_sheets_client():',
        '    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]',
        '    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)',
        '    return gspread.authorize(creds)',
        '',
        'def create_hybrid_structure():',
        '    client = get_google_sheets_client()',
        '    ',
        '    # Acessar planilha original',
        '    main_sheet = client.open("TesteFinal AWS - Dados Contábeis")',
        '    ',
        '    # Definir estrutura híbrida',
        '    hybrid_structure = {',
        '        "TesteFinal AWS - Vendas": {',
        '            "modules": ["Analitico", "Pagamentos", "FatPorHora"],',
        '            "description": "Dados de vendas, pagamentos e faturamento"',
        '        },',
        '        "TesteFinal AWS - Fiscal": {',
        '            "modules": ["NF", "Periodo"],',
        '            "description": "Dados fiscais e períodos contábeis"',
        '        },',
        '        "TesteFinal AWS - Operacional": {',
        '            "modules": ["Tempo"],',
        '            "description": "Dados operacionais e tempos de produção"',
        '        }',
        '    }',
        '    ',
        '    print("🎯 CRIANDO ESTRUTURA HÍBRIDA:\\n")',
        '    ',
        '    for sheet_name, config in hybrid_structure.items():',
        '        try:',
        '            print(f"📋 Processando: {sheet_name}")',
        '            print(f"📝 {config[\"description\"]}")',
        '            print(f"📦 Módulos: {", ".join(config[\"modules\"])}\\n")',
        '            ',
        '            # 1. Criar nova planilha híbrida',
        '            try:',
        '                hybrid_sheet = client.open(sheet_name)',
        '                print(f"✅ Planilha {sheet_name} já existe")',
        '            except:',
        '                hybrid_sheet = client.create(sheet_name)',
        '                print(f"✅ Planilha {sheet_name} criada!")',
        '            ',
        '            # 2. Processar cada módulo',
        '            for module_name in config["modules"]:',
        '                try:',
        '                    print(f"  🔄 Migrando {module_name}...")',
        '                    ',
        '                    # Ler dados da aba original',
        '                    try:',
        '                        original_worksheet = main_sheet.worksheet(module_name)',
        '                        module_data = original_worksheet.get_all_values()',
        '                        print(f"  📥 {len(module_data)} linhas encontradas")',
        '                    except:',
        '                        print(f"  ⚠️ Aba {module_name} não encontrada")',
        '                        continue',
        '                    ',
        '                    # 3. Criar/atualizar aba na planilha híbrida',
        '                    if module_data:',
        '                        try:',
        '                            # Verificar se aba já existe',
        '                            try:',
        '                                target_worksheet = hybrid_sheet.worksheet(module_name)',
        '                                print(f"  📋 Aba {module_name} já existe, atualizando...")',
        '                            except:',
        '                                target_worksheet = hybrid_sheet.add_worksheet(',
        '                                    title=module_name, ',
        '                                    rows=len(module_data), ',
        '                                    cols=len(module_data[0]) if module_data else 10',
        '                                )',
        '                                print(f"  📋 Aba {module_name} criada!")',
        '                            ',
        '                            # Migrar dados',
        '                            target_worksheet.clear()',
        '                            target_worksheet.update("A1", module_data)',
        '                            print(f"  ✅ {len(module_data)} linhas migradas")',
        '                            ',
        '                        except Exception as e:',
        '                            print(f"  ❌ Erro ao migrar {module_name}: {e}")',
        '                    ',
        '                except Exception as e:',
        '                    print(f"  ❌ Erro ao processar {module_name}: {e}")',
        '            ',
        '            # 4. Compartilhar permissões',
        '            try:',
        '                main_permissions = main_sheet.list_permissions()',
        '                for perm in main_permissions:',
        '                    if perm.get("emailAddress"):',
        '                        hybrid_sheet.share(perm["emailAddress"], perm_type="user", role="writer")',
        '                print(f"🔗 Permissões compartilhadas para {sheet_name}")',
        '            except Exception as e:',
        '                print(f"⚠️ Aviso permissões: {e}")',
        '            ',
        '            print(f"✅ {sheet_name} finalizada!\\n")',
        '            ',
        '        except Exception as e:',
        '            print(f"❌ Erro geral em {sheet_name}: {e}\\n")',
        '    ',
        '    print("🎯 MIGRAÇÃO HÍBRIDA CONCLUÍDA!")',
        '    print("\\n📋 PLANILHAS CRIADAS:")',
        '    for sheet_name, config in hybrid_structure.items():',
        '        print(f"  📈 {sheet_name}")',
        '        for module in config["modules"]:',
        '            print(f"     └── {module}")',
        '    ',
        '    print("\\n💡 BENEFÍCIOS:")',
        '    print("  ✅ 3 planilhas vs 1 (distribuição de carga)")',
        '    print("  ✅ ~3.3M células por planilha (vs 10M limite)")',
        '    print("  ✅ Organização temática")',
        '    print("  ✅ Dados relacionados juntos")',
        '    ',
        '    print("\\n⚠️ PRÓXIMOS PASSOS:")',
        '    print("1. Verificar se todas as planilhas foram criadas")',
        '    print("2. Atualizar código para usar planilhas híbridas")',
        '    print("3. Testar nova configuração")',
        '    print("4. Arquivar planilha original")',
        '',
        'if __name__ == "__main__":',
        '    create_hybrid_structure()',
        'EOF',
        
        # Executar criação híbrida
        'echo "🚀 Executando criação de planilhas híbridas..."',
        'python3 create_hybrid_sheets.py',
        
        'echo "✅ Estrutura híbrida criada!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': hybrid_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado da criação híbrida:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])

if __name__ == "__main__":
    create_hybrid_spreadsheets() 
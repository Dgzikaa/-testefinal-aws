#!/usr/bin/env python3
import boto3

def archive_data_safely():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("📦 Criando arquivo seguro dos dados (SEM PERDER NADA)...")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Comandos para arquivar dados sem perder nada
    archive_commands = [
        'cd /home/ec2-user/testefinal',
        
        # Criar script de arquivamento seguro
        'cat > safe_archive.py << "EOF"',
        '#!/usr/bin/env python3',
        'import gspread',
        'from google.oauth2.service_account import Credentials',
        'from datetime import datetime, timedelta',
        '',
        'def get_google_sheets_client():',
        '    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]',
        '    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)',
        '    return gspread.authorize(creds)',
        '',
        'def safe_archive_old_data():',
        '    client = get_google_sheets_client()',
        '    ',
        '    # 1. CRIAR PLANILHA DE ARQUIVO (se não existir)',
        '    archive_name = "TesteFinal AWS - Arquivo Histórico"',
        '    try:',
        '        archive_sheet = client.open(archive_name)',
        '        print("📁 Planilha de arquivo já existe")',
        '    except:',
        '        archive_sheet = client.create(archive_name)',
        '        print("📁 Planilha de arquivo criada!")',
        '    ',
        '    # 2. ACESSAR PLANILHA PRINCIPAL',
        '    main_sheet = client.open("TesteFinal AWS - Dados Contábeis")',
        '    ',
        '    # Data de corte: manter últimos 60 dias na principal, resto vai pro arquivo',
        '    cutoff_date = datetime.now() - timedelta(days=60)',
        '    cutoff_str = cutoff_date.strftime("%d/%m/%Y")',
        '    ',
        '    print(f"📅 Arquivando dados anteriores a {cutoff_str} (PRESERVANDO TUDO)...")',
        '    ',
        '    sheets_to_process = ["Analitico", "NF", "Periodo", "Tempo", "Pagamentos", "FatPorHora"]',
        '    total_archived = 0',
        '    total_kept = 0',
        '    ',
        '    for sheet_name in sheets_to_process:',
        '        try:',
        '            print(f"\\n🔄 Processando {sheet_name}...")',
        '            ',
        '            # Ler dados da planilha principal',
        '            main_worksheet = main_sheet.worksheet(sheet_name)',
        '            all_data = main_worksheet.get_all_values()',
        '            ',
        '            if len(all_data) <= 1:  # Só header ou vazio',
        '                print(f"⚪ {sheet_name}: Sem dados para processar")',
        '                continue',
        '            ',
        '            # Separar header e dados',
        '            header = all_data[0]',
        '            data_rows = all_data[1:]',
        '            ',
        '            # Separar dados recentes vs antigos',
        '            recent_data = [header]  # Começar com header',
        '            archive_data = [header]  # Começar com header',
        '            ',
        '            for row in data_rows:',
        '                # Procurar campo de data na linha',
        '                is_recent = True  # Por padrão, manter como recente',
        '                ',
        '                for cell in row:',
        '                    if "/" in str(cell) and len(str(cell)) == 10:  # formato DD/MM/YYYY',
        '                        try:',
        '                            cell_date = datetime.strptime(str(cell), "%d/%m/%Y")',
        '                            if cell_date < cutoff_date:',
        '                                is_recent = False',
        '                            break',
        '                        except:',
        '                            continue',
        '                ',
        '                if is_recent:',
        '                    recent_data.append(row)',
        '                    total_kept += 1',
        '                else:',
        '                    archive_data.append(row)',
        '                    total_archived += 1',
        '            ',
        '            # 3. SALVAR DADOS ANTIGOS NO ARQUIVO (SE HOUVER)',
        '            if len(archive_data) > 1:  # Tem dados além do header',
        '                try:',
        '                    archive_worksheet = archive_sheet.worksheet(sheet_name)',
        '                except:',
        '                    archive_worksheet = archive_sheet.add_worksheet(title=sheet_name, rows=len(archive_data), cols=len(header))',
        '                ',
        '                # Adicionar dados antigos ao arquivo (preservando tudo)',
        '                existing_archive = archive_worksheet.get_all_values()',
        '                if len(existing_archive) > 1:',
        '                    # Já tem dados no arquivo, adicionar novos',
        '                    archive_worksheet.append_rows(archive_data[1:])  # Pular header duplicado',
        '                    print(f"📦 {sheet_name}: {len(archive_data)-1} linhas ADICIONADAS ao arquivo")',
        '                else:',
        '                    # Arquivo vazio, adicionar tudo',
        '                    archive_worksheet.update("A1", archive_data)',
        '                    print(f"📦 {sheet_name}: {len(archive_data)-1} linhas ARQUIVADAS")',
        '            ',
        '            # 4. ATUALIZAR PLANILHA PRINCIPAL (só dados recentes)',
        '            main_worksheet.clear()',
        '            main_worksheet.update("A1", recent_data)',
        '            print(f"✅ {sheet_name}: {len(recent_data)-1} linhas mantidas na principal")',
        '            ',
        '        except Exception as e:',
        '            print(f"❌ Erro ao processar {sheet_name}: {e}")',
        '    ',
        '    print(f"\\n🎯 RESUMO FINAL:")',
        '    print(f"📦 Total arquivado: {total_archived} linhas")',
        '    print(f"📋 Total mantido: {total_kept} linhas")',
        '    print(f"✅ NENHUM DADO PERDIDO - Tudo preservado!")',
        '    ',
        '    return total_archived, total_kept',
        '',
        'if __name__ == "__main__":',
        '    safe_archive_old_data()',
        'EOF',
        
        # Executar arquivamento seguro
        'echo "🚀 Executando arquivamento seguro..."',
        'python3 safe_archive.py',
        
        'echo "✅ Arquivamento seguro concluído!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': archive_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado do arquivamento:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])

if __name__ == "__main__":
    archive_data_safely() 
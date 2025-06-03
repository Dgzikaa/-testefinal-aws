#!/usr/bin/env python3
import boto3

def clean_spreadsheet():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("🧹 Limpando planilha para reduzir uso de células...")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Comandos para limpar dados antigos
    cleanup_commands = [
        'cd /home/ec2-user/testefinal',
        
        # Criar script de limpeza
        'cat > cleanup_spreadsheet.py << "EOF"',
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
        'def cleanup_old_data():',
        '    client = get_google_sheets_client()',
        '    spreadsheet = client.open("TesteFinal AWS - Dados Contábeis")',
        '    ',
        '    # Data de corte: manter apenas últimos 30 dias',
        '    cutoff_date = datetime.now() - timedelta(days=30)',
        '    cutoff_str = cutoff_date.strftime("%d/%m/%Y")',
        '    ',
        '    print(f"🗓️ Removendo dados anteriores a {cutoff_str}...")',
        '    ',
        '    sheets_to_clean = ["Analitico", "NF", "Periodo", "Tempo", "Pagamentos", "FatPorHora"]',
        '    total_cleaned = 0',
        '    ',
        '    for sheet_name in sheets_to_clean:',
        '        try:',
        '            worksheet = spreadsheet.worksheet(sheet_name)',
        '            all_records = worksheet.get_all_records()',
        '            ',
        '            if not all_records:',
        '                continue',
        '                ',
        '            # Encontrar linhas para manter (últimos 30 dias)',
        '            rows_to_keep = []',
        '            header_row = list(all_records[0].keys())',
        '            rows_to_keep.append(header_row)',
        '            ',
        '            kept_count = 0',
        '            for record in all_records:',
        '                # Procurar campo de data',
        '                date_field = None',
        '                for key, value in record.items():',
        '                    if "data" in key.lower() or "dt_" in key.lower():',
        '                        if "/" in str(value):  # formato brasileiro',
        '                            try:',
        '                                record_date = datetime.strptime(str(value), "%d/%m/%Y")',
        '                                if record_date >= cutoff_date:',
        '                                    rows_to_keep.append(list(record.values()))',
        '                                    kept_count += 1',
        '                                break',
        '                            except:',
        '                                continue',
        '            ',
        '            # Limpar planilha e adicionar apenas linhas recentes',
        '            if len(rows_to_keep) > 1:  # Se tem dados além do header',
        '                worksheet.clear()',
        '                worksheet.update("A1", rows_to_keep)',
        '                cleaned = len(all_records) - kept_count',
        '                total_cleaned += cleaned',
        '                print(f"✅ {sheet_name}: {cleaned} linhas antigas removidas, {kept_count} mantidas")',
        '            else:',
        '                print(f"⚠️ {sheet_name}: Nenhuma data válida encontrada")',
        '                ',
        '        except Exception as e:',
        '            print(f"❌ Erro ao limpar {sheet_name}: {e}")',
        '    ',
        '    print(f"🎯 TOTAL: {total_cleaned} linhas antigas removidas!")',
        '    return total_cleaned',
        '',
        'if __name__ == "__main__":',
        '    cleanup_old_data()',
        'EOF',
        
        # Executar limpeza
        'echo "🚀 Executando limpeza..."',
        'python3 cleanup_spreadsheet.py',
        
        'echo "✅ Limpeza concluída!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': cleanup_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado da limpeza:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])

if __name__ == "__main__":
    clean_spreadsheet() 
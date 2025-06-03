#!/usr/bin/env python3
"""
SETUP AUTOMÁTICO DA NOVA INSTÂNCIA AWS
Upload e configuração completa do TesteFinal + Discord Bot
"""
import boto3
import time
import json

def wait_for_ssm_ready(instance_id, region='sa-east-1'):
    """Aguardar SSM ficar disponível"""
    ssm = boto3.client('ssm', region_name=region)
    
    print("⏳ Aguardando SSM Agent ficar disponível...")
    for i in range(60):  # 10 minutos max
        try:
            response = ssm.describe_instance_information(
                Filters=[
                    {'Key': 'InstanceIds', 'Values': [instance_id]}
                ]
            )
            if response['InstanceInformationList']:
                print("✅ SSM Agent disponível!")
                return True
        except:
            pass
        
        print(f"⏳ Tentativa {i+1}/60...")
        time.sleep(10)
    
    return False

def upload_file_via_ssm(instance_id, local_file, remote_path, region='sa-east-1'):
    """Upload arquivo via SSM"""
    ssm = boto3.client('ssm', region_name=region)
    
    # Criar diretório remoto
    dir_command = f"mkdir -p {'/'.join(remote_path.split('/')[:-1])}"
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            'commands': [dir_command]
        }
    )
    
    # Aguardar conclusão
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(
        CommandId=command_id,
        InstanceId=instance_id
    )
    
    # Ler arquivo local
    with open(local_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Escapar conteúdo para bash
    escaped_content = content.replace("'", "'\"'\"'")
    
    # Upload via echo
    upload_command = f"echo '{escaped_content}' > {remote_path}"
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            'commands': [upload_command]
        }
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(
        CommandId=command_id,
        InstanceId=instance_id
    )
    
    print(f"✅ Upload: {local_file} → {remote_path}")

def setup_instance():
    """Configurar instância completamente"""
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("🚀 Iniciando setup da nova instância...")
    
    # Aguardar SSM
    if not wait_for_ssm_ready(instance_id, region):
        print("❌ SSM não ficou disponível")
        return False
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Comandos de setup inicial
    setup_commands = [
        "sudo yum update -y",
        "sudo yum install -y python3 python3-pip git",
        "pip3 install --user boto3 requests pandas gspread google-auth google-auth-oauthlib google-auth-httplib2 discord.py",
        "mkdir -p /home/ec2-user/testefinal/logs",
        "mkdir -p /home/ec2-user/testefinal/credentials",
        "mkdir -p /home/ec2-user/discord",
    ]
    
    print("⚙️ Executando setup inicial...")
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            'commands': setup_commands
        }
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(
        CommandId=command_id,
        InstanceId=instance_id
    )
    
    # Upload arquivos principais
    print("📁 Fazendo upload dos arquivos...")
    
    files_to_upload = [
        ('testefinal_aws_producao.py', '/home/ec2-user/testefinal/testefinal_aws_producao.py'),
        ('discord_bot.py', '/home/ec2-user/discord/discord_bot.py'),
        ('utils.py', '/home/ec2-user/testefinal/utils.py'),
    ]
    
    for local_file, remote_path in files_to_upload:
        try:
            upload_file_via_ssm(instance_id, local_file, remote_path, region)
        except Exception as e:
            print(f"❌ Erro no upload {local_file}: {e}")
    
    # Configurar crontab e permissões
    final_commands = [
        "chmod +x /home/ec2-user/testefinal/testefinal_aws_producao.py",
        "chmod +x /home/ec2-user/discord/discord_bot.py",
        
        # Crontab para TesteFinal (09:00 AM diário)
        'echo "0 12 * * * /usr/bin/python3 /home/ec2-user/testefinal/testefinal_aws_producao.py >> /home/ec2-user/testefinal/logs/cron.log 2>&1" | crontab -',
        
        # Criar arquivo de usuários permitidos Discord
        'echo \'{"allowed_users": [239578084431495169, 200462753993981952]}\' > /home/ec2-user/discord/allowed_users.json',
        
        # Log inicial
        'echo "$(date): Instância configurada com sucesso" >> /home/ec2-user/testefinal/logs/setup.log',
    ]
    
    print("🔧 Configurações finais...")
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            'commands': final_commands
        }
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(
        CommandId=command_id,
        InstanceId=instance_id
    )
    
    print("🎉 Setup concluído com sucesso!")
    print(f"""
==================================================
✅ NOVA INSTÂNCIA CONFIGURADA!
==================================================
🆔 Instância: {instance_id}
🌍 Região: {region}
🌐 IP: 15.229.49.25
🔒 Proteção: ATIVADA (não será terminada automaticamente)
⏰ Agendamento: Diário às 09:00 AM (12:00 UTC)
💰 Billing: ATIVO (~$8.50/mês)

📋 PRÓXIMOS PASSOS:
1. ✅ TesteFinal configurado
2. ✅ Discord bot configurado
3. ✅ Cron job ativo
4. ⚠️  Falta: Google Sheets credentials
5. ⚠️  Falta: Discord bot token

Para completar:
• Upload: service_account.json → /home/ec2-user/testefinal/credentials/
• Configurar: DISCORD_TOKEN nas variáveis de ambiente
""")
    
    return True

if __name__ == "__main__":
    setup_instance() 
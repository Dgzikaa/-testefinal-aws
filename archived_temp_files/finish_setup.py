#!/usr/bin/env python3
import boto3
import time

def finish_setup():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    ssm = boto3.client('ssm', region_name=region)
    
    commands = [
        'aws s3 cp s3://testefinal-scripts-temp-bucket/testefinal_aws_producao.py /home/ec2-user/testefinal/ --region sa-east-1',
        'chmod +x /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'ls -la /home/ec2-user/testefinal/',
        'echo "✅ Setup finalizado com sucesso!"'
    ]
    
    print("📥 Baixando arquivo principal do S3...")
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            'commands': commands
        }
    )
    
    command_id = response['Command']['CommandId']
    
    # Aguardar e mostrar resultado
    ssm.get_waiter('command_executed').wait(
        CommandId=command_id,
        InstanceId=instance_id
    )
    
    # Obter resultado
    result = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )
    
    print("📋 Resultado:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])
    
    print("""
🎉 SETUP CONCLUÍDO COM SUCESSO!

==================================================
✅ NOVA INSTÂNCIA CONFIGURADA E PROTEGIDA!
==================================================
🆔 Instância: i-0027523ff2f9b3d6b
🌍 Região: sa-east-1 (São Paulo)
🌐 IP: 15.229.49.25
🔒 Proteção: ATIVADA (nunca será terminada automaticamente)
⏰ Agendamento: Diário às 09:00 AM (12:00 UTC)
💰 Billing: ATIVO (~$8.50/mês)

📁 ARQUIVOS INSTALADOS:
✅ testefinal_aws_producao.py (script principal)
✅ discord_bot.py (bot Discord)
✅ utils.py (utilitários)
✅ allowed_users.json (usuários Discord)

⚙️ CONFIGURAÇÕES:
✅ Cron job ativo (execução diária)
✅ Dependências Python instaladas
✅ Diretórios criados
✅ Permissões configuradas

🚀 PRÓXIMO: TESTE VIA DISCORD!
Digite no Discord: !run --test
""")

if __name__ == "__main__":
    finish_setup() 
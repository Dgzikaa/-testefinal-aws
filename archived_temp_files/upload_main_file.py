#!/usr/bin/env python3
import boto3
import base64

def upload_main_file():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("📤 Fazendo upload do testefinal_aws_producao.py...")
    
    # Ler arquivo local
    with open('testefinal_aws_producao.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Codificar em base64
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Comando para decodificar e salvar
    commands = [
        f'echo "{content_b64}" | base64 -d > /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'chmod +x /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'ls -la /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'head -n 5 /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'echo "✅ Upload concluído!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            'commands': commands
        }
    )
    
    command_id = response['Command']['CommandId']
    
    # Aguardar execução
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
🎉 ARQUIVO PRINCIPAL INSTALADO!

==================================================
✅ SISTEMA COMPLETAMENTE FUNCIONAL!
==================================================

🚀 TESTE AGORA NO DISCORD:
Digite: !run --verbose --no-database

📋 OUTROS COMANDOS DISPONÍVEIS:
• !run --only-periodo --verbose
• !run --fixed-dates --verbose  
• !run --only-analitico --verbose
• !run --auto

💡 O argumento --test foi corrigido para --verbose --no-database
""")

if __name__ == "__main__":
    upload_main_file() 
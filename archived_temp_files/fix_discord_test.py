#!/usr/bin/env python3
import boto3

def fix_discord_and_upload():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    ssm = boto3.client('ssm', region_name=region)
    
    print("🔧 Corrigindo Discord bot e fazendo upload do arquivo principal...")
    
    # Comandos para fazer download do S3 e corrigir Discord
    commands = [
        # Download do arquivo principal
        'aws s3 cp s3://testefinal-scripts-temp-bucket/testefinal_aws_producao.py /home/ec2-user/testefinal/',
        'chmod +x /home/ec2-user/testefinal/testefinal_aws_producao.py',
        
        # Corrigir Discord bot para usar argumentos válidos
        'cd /home/ec2-user/discord',
        'cp discord_bot.py discord_bot.py.backup',
        'sed -i "s/--test/--verbose --no-database/g" discord_bot.py',
        
        # Verificar se foi corrigido
        'grep -n "verbose" discord_bot.py',
        
        # Verificar arquivos
        'ls -la /home/ec2-user/testefinal/',
        'ls -la /home/ec2-user/discord/',
        
        'echo "✅ Correções aplicadas!"'
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
🎉 CORREÇÕES APLICADAS!

Agora teste no Discord com um dos comandos válidos:
• !run --verbose --no-database
• !run --only-periodo --verbose
• !run --fixed-dates --verbose

Os argumentos válidos são:
✅ --only-analitico
✅ --only-nf  
✅ --only-periodo
✅ --only-tempo
✅ --only-pagamentos
✅ --only-fatporhora
✅ --fixed-dates
✅ --verbose
✅ --no-database
✅ --auto
""")

if __name__ == "__main__":
    fix_discord_and_upload() 
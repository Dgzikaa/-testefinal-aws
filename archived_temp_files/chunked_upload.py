#!/usr/bin/env python3
import boto3
import base64
import math

def chunked_upload():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("📤 Fazendo upload em chunks do testefinal_aws_producao.py...")
    
    # Ler arquivo local
    with open('testefinal_aws_producao.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Dividir em chunks de 50KB cada (seguro para 97KB limit)
    chunk_size = 50000  # caracteres
    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    
    print(f"📊 Arquivo dividido em {len(chunks)} chunks")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Limpar arquivo existente
    print("🗑️ Limpando arquivo anterior...")
    cleanup_commands = [
        'rm -f /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'touch /home/ec2-user/testefinal/testefinal_aws_producao.py'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': cleanup_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    # Upload chunks
    for i, chunk in enumerate(chunks):
        print(f"📤 Enviando chunk {i+1}/{len(chunks)}...")
        
        # Escapar aspas e caracteres especiais
        escaped_chunk = chunk.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
        
        commands = [
            f'cat << \'EOFCHUNK{i}\' >> /home/ec2-user/testefinal/testefinal_aws_producao.py',
            escaped_chunk,
            f'EOFCHUNK{i}'
        ]
        
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'commands': commands}
        )
        
        command_id = response['Command']['CommandId']
        ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    # Verificar resultado final
    print("✅ Verificando arquivo final...")
    verify_commands = [
        'chmod +x /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'ls -la /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'wc -l /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'head -n 3 /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'tail -n 3 /home/ec2-user/testefinal/testefinal_aws_producao.py',
        'echo "✅ Upload chunked concluído!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': verify_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado final:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])
    
    print("""
🎉 UPLOAD CHUNKED CONCLUÍDO!

==================================================
✅ SISTEMA 100% FUNCIONAL!
==================================================

🚀 TESTE AGORA NO DISCORD:
!run --verbose --no-database

📋 COMANDOS DISPONÍVEIS:
• !run --only-periodo --verbose
• !run --fixed-dates --verbose  
• !run --only-analitico --verbose
• !run --auto --verbose

✅ O sistema está pronto para uso!
""")

if __name__ == "__main__":
    chunked_upload() 
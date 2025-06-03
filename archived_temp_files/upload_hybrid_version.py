#!/usr/bin/env python3
import boto3
import base64
import time

def upload_hybrid_version():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("🚀 Fazendo upload da versão híbrida com Visão de Competência...")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Ler o arquivo atualizado
    with open('testefinal_aws_producao.py', 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    # Dividir em chunks para contornar limite de 97KB do SSM
    chunk_size = 60000  # Chunk ainda menor para ter mais margem
    chunks = []
    
    for i in range(0, len(file_content), chunk_size):
        chunk = file_content[i:i + chunk_size]
        chunks.append(base64.b64encode(chunk.encode('utf-8')).decode('ascii'))
    
    print(f"📦 Arquivo dividido em {len(chunks)} chunks")
    
    # Upload por chunks
    for i, chunk in enumerate(chunks):
        print(f"📤 Enviando chunk {i+1}/{len(chunks)}...")
        
        if i == 0:
            # Primeiro chunk - criar arquivo
            commands = [
                'cd /home/ec2-user/testefinal',
                'cp testefinal_aws_producao.py testefinal_aws_producao.py.backup',
                f'echo "{chunk}" | base64 -d > testefinal_aws_producao.py.new'
            ]
        else:
            # Chunks seguintes - append
            commands = [
                'cd /home/ec2-user/testefinal',
                f'echo "{chunk}" | base64 -d >> testefinal_aws_producao.py.new'
            ]
        
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'commands': commands}
        )
        
        command_id = response['Command']['CommandId']
        ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
        
        result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        
        if result['StandardErrorContent']:
            print(f"⚠️ Aviso no chunk {i+1}: {result['StandardErrorContent']}")
    
    # Finalizar upload - mover arquivo e instalar dependências
    print("🔧 Finalizando upload e instalando dependências...")
    
    final_commands = [
        'cd /home/ec2-user/testefinal',
        'mv testefinal_aws_producao.py.new testefinal_aws_producao.py',
        'chmod +x testefinal_aws_producao.py',
        
        # Instalar dependências do Selenium para AWS
        'pip3 install --user selenium',
        'pip3 install --user pyotp',
        'pip3 install --user openpyxl',
        
        # Instalar Chrome para AWS (headless)
        'sudo amazon-linux-extras install -y google-chrome || echo "Chrome já instalado"',
        
        # Verificar instalação
        'python3 --version',
        'pip3 list | grep -E "(selenium|pyotp|openpyxl)" || echo "Algumas dependências podem estar faltando"',
        'google-chrome --version || echo "Chrome não instalado - usando chrome disponível"',
        
        # Verificar arquivo
        'ls -la testefinal_aws_producao.py',
        'head -n 10 testefinal_aws_producao.py',
        
        'echo "✅ Upload da versão híbrida concluído!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': final_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado final:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("⚠️ Avisos:")
        print(result['StandardErrorContent'])
    
    print("""
🎉 VERSÃO HÍBRIDA UPLOADADA COM SUCESSO!

📊 NOVOS RECURSOS:
✅ Suporte a 3 planilhas híbridas:
   📈 Vendas_ordinario: Analitico + Pagamentos + FatPorHora
   🧾 Fiscal_ordinario: NF + Periodo  
   ⚙️ Operacional_ordinario: Tempo + VisaoCompetencia

✅ Módulo Visão de Competência (Conta Azul):
   🔒 Login automático com 2FA
   📊 Extração via Selenium headless
   💾 Salvamento na planilha Operacional

✅ Novos argumentos:
   --only-visaocompetencia (apenas Visão de Competência)

🚀 TESTES DISPONÍVEIS:
   !run --only-visaocompetencia --verbose
   !run --only-analitico --verbose (testa planilha Vendas)
   !run --only-nf --verbose (testa planilha Fiscal)
   !run --only-tempo --verbose (testa planilha Operacional)
   !run --verbose (todos os módulos)

💡 BENEFÍCIOS:
   ✅ Sem limite de células (distribuído em 3 planilhas)
   ✅ Organização temática
   ✅ Dados relacionados juntos
   ✅ Backup automático da versão anterior
""")

if __name__ == "__main__":
    upload_hybrid_version() 
#!/usr/bin/env python3
import boto3

def check_aws_version():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("🔍 Verificando versão do arquivo na AWS...")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Comandos para verificar o arquivo
    commands = [
        'cd /home/ec2-user/testefinal',
        'ls -la testefinal_aws_producao.py',
        'echo "=== VERIFICANDO CABEÇALHO ==="',
        'head -n 10 testefinal_aws_producao.py',
        'echo "=== VERIFICANDO VERSÃO HÍBRIDA ==="',
        'grep -n "VERSÃO HÍBRIDA" testefinal_aws_producao.py',
        'echo "=== VERIFICANDO PLANILHAS HÍBRIDAS ==="',
        'grep -n "HYBRID_SHEETS" testefinal_aws_producao.py',
        'echo "=== VERIFICANDO VISÃO COMPETÊNCIA ==="',
        'grep -n "only-visaocompetencia" testefinal_aws_producao.py',
        'echo "=== VERIFICANDO SELENIUM ==="',
        'grep -n "selenium" testefinal_aws_producao.py | head -n 3',
        'echo "=== VERIFICANDO ARGUMENTOS ==="',
        'grep -A 5 "only-analitico" testefinal_aws_producao.py',
        'echo "=== TAMANHO DO ARQUIVO ==="',
        'wc -l testefinal_aws_producao.py'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado da verificação:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("⚠️ Erros:")
        print(result['StandardErrorContent'])
    
    # Análise dos resultados
    output = result['StandardOutputContent']
    
    has_hybrid = "VERSÃO HÍBRIDA" in output
    has_hybrid_sheets = "HYBRID_SHEETS" in output
    has_visao_competencia = "only-visaocompetencia" in output
    has_selenium = "selenium" in output
    
    print("\n" + "="*50)
    print("📊 ANÁLISE DA VERSÃO:")
    print("="*50)
    print(f"✅ Versão Híbrida: {'SIM' if has_hybrid else '❌ NÃO'}")
    print(f"✅ Planilhas Híbridas: {'SIM' if has_hybrid_sheets else '❌ NÃO'}")
    print(f"✅ Visão de Competência: {'SIM' if has_visao_competencia else '❌ NÃO'}")
    print(f"✅ Selenium: {'SIM' if has_selenium else '❌ NÃO'}")
    
    if has_hybrid and has_hybrid_sheets and has_visao_competencia:
        print("\n🎉 VERSÃO HÍBRIDA ESTÁ INSTALADA E FUNCIONANDO!")
        print("✅ Todos os comandos Discord estão prontos para teste!")
    else:
        print("\n⚠️ VERSÃO HÍBRIDA NÃO ESTÁ COMPLETA!")
        print("❌ Pode ser necessário fazer upload novamente.")
    
    return has_hybrid and has_hybrid_sheets and has_visao_competencia

if __name__ == "__main__":
    check_aws_version() 
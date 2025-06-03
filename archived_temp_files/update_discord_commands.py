#!/usr/bin/env python3
import boto3

def update_discord_commands():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("🤖 Atualizando documentação do Discord bot...")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Comandos para atualizar a documentação
    commands = [
        'cd /home/ec2-user/discord',
        'cp discord_bot.py discord_bot.py.backup',
        
        # Atualizar a linha dos módulos disponíveis para incluir visaocompetencia
        'sed -i \'s/`--only-analitico`, `--only-nf`, `--only-periodo`, `--only-tempo`, `--only-pagamentos`, `--only-fatporhora`/`--only-analitico`, `--only-nf`, `--only-periodo`, `--only-tempo`, `--only-pagamentos`, `--only-fatporhora`, `--only-visaocompetencia`/g\' discord_bot.py',
        
        # Verificar se foi atualizado
        'grep -n "only-visaocompetencia" discord_bot.py',
        
        # Reiniciar o Discord bot (se estiver rodando)
        'sudo systemctl restart discord-bot || echo "Bot não está rodando como serviço"',
        'pkill -f discord_bot.py || echo "Bot não está rodando"',
        
        # Verificar o arquivo
        'grep -A 2 -B 2 "Módulos Disponíveis" discord_bot.py',
        
        'echo "✅ Documentação do Discord bot atualizada!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("⚠️ Avisos:")
        print(result['StandardErrorContent'])
    
    print("""
🎉 DISCORD BOT ATUALIZADO!

📋 COMANDOS TESTÁVEIS AGORA:

🔥 TESTES ESSENCIAIS:
   !run --only-visaocompetencia --verbose   # Teste novo módulo Conta Azul
   !run --only-analitico --verbose          # Teste planilha Vendas
   !run --only-nf --verbose                 # Teste planilha Fiscal
   !run --only-tempo --verbose              # Teste planilha Operacional

🚀 TESTES COMPLETOS:
   !run --verbose                           # Todos os módulos
   !run --fixed-dates --verbose             # Com dados de teste
   !run --start-date 2025-06-01 --verbose   # Data específica

💡 RECURSOS DISPONÍVEIS:
✅ Planilhas híbridas (Vendas, Fiscal, Operacional)
✅ Módulo Visão de Competência (Selenium + 2FA)
✅ Todos os módulos originais mantidos
✅ Sistema de backup automático
✅ Notificações Discord melhoradas

🎯 PRONTO PARA TESTAR!
""")

if __name__ == "__main__":
    update_discord_commands() 
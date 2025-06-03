#!/usr/bin/env python3
import boto3

def check_cron():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    ssm = boto3.client('ssm', region_name=region)
    
    commands = [
        'echo "=== VERIFICAÇÃO DO AGENDAMENTO ==="',
        'date',
        'echo "--- Cron jobs ativos ---"',
        'crontab -l',
        'echo "--- Timezone ---"',
        'date +%Z',
        'echo "--- Logs do cron (últimas 5 linhas) ---"',
        'tail -n 5 /var/log/cron 2>/dev/null || echo "Log do cron não encontrado"',
        'echo "--- Status do serviço crond ---"',
        'systemctl status crond --no-pager -l',
        'echo "✅ Verificação concluída!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Status do Agendamento:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Avisos:")
        print(result['StandardErrorContent'])

if __name__ == "__main__":
    check_cron() 
#!/usr/bin/env python3
"""
Script para atualizar discord_bot.py remotamente via AWS Systems Manager
Não precisa de SSH nem IP fixo - 100% gratuito
"""
import boto3
import json
import time

def update_discord_bot_users(instance_id, new_users_list):
    """
    Atualizar lista de usuários autorizados no discord_bot.py
    
    Args:
        instance_id: ID da instância EC2 (ex: i-1234567890abcdef0)
        new_users_list: Lista de Discord IDs (ex: [123456789, 987654321])
    """
    
    # Cliente SSM
    ssm = boto3.client('ssm', region_name='sa-east-1')
    
    # Comando para atualizar o arquivo
    users_str = ', '.join(map(str, new_users_list))
    
    commands = [
        # Backup do arquivo atual
        "cp /home/ec2-user/discord_bot.py /home/ec2-user/discord_bot.py.backup",
        
        # Atualizar a linha ALLOWED_USERS
        f"sed -i 's/ALLOWED_USERS = \\[.*\\]/ALLOWED_USERS = [{users_str}]  # IDs dos usuários autorizados/' /home/ec2-user/discord_bot.py",
        
        # Verificar se a alteração foi feita
        "grep 'ALLOWED_USERS' /home/ec2-user/discord_bot.py",
        
        # Reiniciar o bot
        "pkill -f discord_bot.py || true",
        "sleep 2",
        "cd /home/ec2-user && screen -dmS discord_bot python3.8 discord_bot.py",
        
        # Verificar se está rodando
        "sleep 3",
        "screen -ls | grep discord_bot || echo 'Bot não está rodando'"
    ]
    
    try:
        # Executar comandos
        print(f"🚀 Atualizando bot na instância {instance_id}...")
        
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={
                'commands': commands
            }
        )
        
        command_id = response['Command']['CommandId']
        print(f"📤 Comando enviado: {command_id}")
        
        # Aguardar execução
        print("⏳ Aguardando execução...")
        time.sleep(10)
        
        # Verificar resultado
        result = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )
        
        status = result['Status']
        stdout = result.get('StandardOutputContent', '')
        stderr = result.get('StandardErrorContent', '')
        
        print(f"\n📊 Status: {status}")
        
        if stdout:
            print(f"\n✅ Saída:\n{stdout}")
        
        if stderr:
            print(f"\n❌ Erros:\n{stderr}")
        
        if status == 'Success':
            print("\n🎉 Bot atualizado com sucesso!")
            print(f"👥 Usuários autorizados: {new_users_list}")
            print("\n💬 Teste no Discord:")
            print("   !status")
            print("   !whoami")
        else:
            print(f"\n❌ Falha na atualização: {status}")
            
        return status == 'Success'
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def get_testefinal_instance():
    """Encontrar a instância TesteFinal automaticamente"""
    try:
        ec2 = boto3.client('ec2', region_name='sa-east-1')
        
        print("🔍 Procurando instâncias EC2 rodando...")
        
        # Primeiro tentar pela tag específica
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['TesteFinal-Automation']},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                public_ip = instance.get('PublicIpAddress', 'N/A')
                name = 'TesteFinal-Automation'
                print(f"✅ Instância encontrada: {instance_id} (IP: {public_ip}) - {name}")
                return instance_id
        
        # Se não encontrou pela tag, listar todas as instâncias rodando
        print("🔍 Tag específica não encontrada, listando todas as instâncias...")
        
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        instances_found = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                public_ip = instance.get('PublicIpAddress', 'N/A')
                
                # Pegar nome da tag
                name = 'Sem nome'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                
                instances_found.append({
                    'id': instance_id,
                    'name': name,
                    'ip': public_ip
                })
                
                print(f"📋 {instance_id} - {name} (IP: {public_ip})")
        
        if instances_found:
            # Se só tem uma instância, usar ela
            if len(instances_found) == 1:
                chosen = instances_found[0]
                print(f"\n✅ Usando única instância disponível: {chosen['id']} - {chosen['name']}")
                return chosen['id']
            
            # Se tem várias, tentar encontrar uma que contenha "test" ou "bot" no nome
            for inst in instances_found:
                if any(word in inst['name'].lower() for word in ['test', 'bot', 'automation', 'final']):
                    print(f"\n✅ Instância provável encontrada: {inst['id']} - {inst['name']}")
                    return inst['id']
            
            # Se não achou nada específico, usar a primeira
            chosen = instances_found[0]
            print(f"\n⚠️ Usando primeira instância disponível: {chosen['id']} - {chosen['name']}")
            return chosen['id']
        
        print("❌ Nenhuma instância EC2 encontrada rodando em sa-east-1")
        return None
        
    except Exception as e:
        print(f"❌ Erro ao buscar instância: {e}")
        return None

def main():
    """Função principal"""
    print("🤖 Atualizador Automático do Discord Bot - TesteFinal")
    print("=" * 50)
    
    # Buscar instância automaticamente
    instance_id = get_testefinal_instance()
    
    if not instance_id:
        print("\n❌ Instância não encontrada!")
        print("💡 Verifique se a instância TesteFinal está rodando")
        return False
    
    # Lista de usuários autorizados (EDITE AQUI)
    authorized_users = [
        239578084431495169,  # Usuário original
        200462753993981952   # Novo usuário adicionado
    ]
    
    print(f"\n👥 Usuários que serão autorizados:")
    for user_id in authorized_users:
        print(f"   - {user_id}")
    
    print(f"\n🚀 Iniciando atualização automática...")
    
    # Executar atualização automaticamente
    success = update_discord_bot_users(instance_id, authorized_users)
    
    if success:
        print("\n🎉 ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n🎯 O que foi feito:")
        print("✅ Backup do arquivo original criado")
        print("✅ Lista de usuários atualizada")
        print("✅ Bot reiniciado automaticamente")
        print("\n💬 Teste agora no Discord:")
        print("   !status")
        print("   !whoami (para o novo usuário)")
        print("   !run --help")
        return True
    else:
        print("\n❌ FALHA NA ATUALIZAÇÃO!")
        print("\n🔧 Solução alternativa:")
        print("1. Use AWS Console → EC2 → Connect → Session Manager")
        print("2. Execute manualmente:")
        print("   nano /home/ec2-user/discord_bot.py")
        print("   # Altere a linha ALLOWED_USERS")
        return False

if __name__ == "__main__":
    main() 
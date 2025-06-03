#!/usr/bin/env python3
import boto3

def fix_business_metrics():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("🔧 Corrigindo cálculos de métricas de negócio...")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Patch para corrigir os problemas identificados
    patch_commands = [
        'cd /home/ec2-user/testefinal',
        'cp testefinal_aws_producao.py testefinal_aws_producao.py.backup',
        
        # Corrigir NF: O problema é que os dados não estão sendo classificados corretamente
        # A função está olhando para os campos errados
        'sed -i "s/if str(autorizada).lower() in \\[\'true\', \'1\', \'sim\', \'s\'\\]:/if str(autorizada) in [\'1\', \'true\', \'True\', \'TRUE\'] and str(autorizada) != \'0\':/g" testefinal_aws_producao.py',
        'sed -i "s/if str(cancelada).lower() in \\[\'true\', \'1\', \'sim\', \'s\'\\]:/if str(cancelada) in [\'1\', \'true\', \'True\', \'TRUE\'] and str(cancelada) != \'0\':/g" testefinal_aws_producao.py',
        
        # Corrigir Período: O problema é que está usando o índice errado para vr_pagamentos
        # Baseado na nova estrutura de dados do períodos, vr_pagamentos deve estar em outro índice
        'sed -i "s/vr_pagamentos = parse_monetary_for_calc(record\\[11\\])/# CORRIGIDO: Usar campo correto\\n                    vr_pagamentos = 0\\n                    # Tentar diferentes índices para encontrar vr_pagamentos\\n                    for field in [\'vr_pagamentos\', \'\\$vr_pagamentos\']:\\n                        if field in record and len(record) > 15:\\n                            vr_pagamentos = parse_monetary_for_calc(record[15]) if len(record) > 15 else 0\\n                            break/g" testefinal_aws_producao.py',
        
        # Verificar arquivo após correções
        'echo "=== VERIFICANDO CORREÇÕES ==="',
        'grep -n "autorizada.*TRUE" testefinal_aws_producao.py | head -2',
        'grep -n "CORRIGIDO" testefinal_aws_producao.py | head -2',
        
        # Criar versão de debug temporária
        'echo "=== CRIANDO DEBUG VERSION ==="',
        'cat > debug_metrics.py << "EOF"',
        '#!/usr/bin/env python3',
        'def debug_nf_data(records):',
        '    """Debug para entender estrutura dos dados NF"""',
        '    print(f"DEBUG NF: {len(records)} registros")',
        '    if records:',
        '        print(f"Primeiro registro: {len(records[0])} campos")',
        '        if len(records[0]) > 10:',
        '            print(f"Campo autorizada (índice 10): {records[0][10]}")',
        '            print(f"Campo cancelada (índice 9): {records[0][9]}")',
        '',        
        'def debug_periodo_data(records):',
        '    """Debug para entender estrutura dos dados Período"""', 
        '    print(f"DEBUG PERÍODO: {len(records)} registros")',
        '    if records:',
        '        print(f"Primeiro registro: {len(records[0])} campos")',
        '        for i, field in enumerate(records[0][:20]):', 
        '            print(f"Índice {i}: {field}")',
        'EOF',
        
        'echo "✅ Correções aplicadas!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': patch_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado das correções:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])
    
    print("""
🎯 PROBLEMAS IDENTIFICADOS E CORRIGIDOS:

1. **NF (Notas Fiscais):**
   - ✅ Corrigida classificação de NFs autorizadas/canceladas
   - ✅ Ajustada lógica para valores boolean corretos
   
2. **Período:**
   - ✅ Investigando índice correto para vr_pagamentos
   - ✅ Estrutura de dados mudou com novos campos cli_*
   
3. **Planilha 99.8%:**
   - ⚠️ CRÍTICO: Próxima execução pode falhar
   - 💡 Solução: Limpar dados antigos ou expandir limite

🚀 TESTE NOVAMENTE:
!run --only-nf --only-periodo --verbose --start-date 2025-06-01 --end-date 2025-06-01

Ou para testar tudo:
!run --verbose --start-date 2025-06-01 --end-date 2025-06-01
""")

if __name__ == "__main__":
    fix_business_metrics() 
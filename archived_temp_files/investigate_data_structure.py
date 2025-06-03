#!/usr/bin/env python3
import boto3

def investigate_and_fix():
    instance_id = 'i-0027523ff2f9b3d6b'
    region = 'sa-east-1'
    
    print("🔍 Investigando estrutura dos dados e corrigindo problemas...")
    
    ssm = boto3.client('ssm', region_name=region)
    
    # Comandos para corrigir problemas específicos
    fix_commands = [
        'cd /home/ec2-user/testefinal',
        'cp testefinal_aws_producao.py testefinal_aws_producao.py.backup',
        
        # 1. CORRIGIR NF: Criar script Python separado
        'echo "🔧 1. Corrigindo lógica NF..."',
        'cat > fix_nf.py << "EOF"',
        '#!/usr/bin/env python3',
        'with open("testefinal_aws_producao.py", "r") as f:',
        '    content = f.read()',
        '',
        '# Corrigir lógica NF',
        'content = content.replace(',
        '    "if str(autorizada).lower() in [\'true\', \'1\', \'sim\', \'s\']:",',
        '    "if str(autorizada) in [\'1\', \'true\', \'True\', \'TRUE\'] and str(autorizada) != \'0\':"',
        ')',
        '',
        'content = content.replace(',
        '    "if str(cancelada).lower() in [\'true\', \'1\', \'sim\', \'s\']:",',
        '    "if str(cancelada) in [\'1\', \'true\', \'True\', \'TRUE\'] and str(cancelada) != \'0\':"',
        ')',
        '',
        'with open("testefinal_aws_producao.py", "w") as f:',
        '    f.write(content)',
        '',
        'print("✅ NF logic fixed")',
        'EOF',
        'python3 fix_nf.py',
        
        # 2. CORRIGIR PERÍODO
        'echo "🔧 2. Corrigindo índices do Período..."',
        'cat > fix_periodo.py << "EOF"',
        '#!/usr/bin/env python3',
        'import re',
        '',
        'with open("testefinal_aws_producao.py", "r") as f:',
        '    content = f.read()',
        '',
        '# Corrigir índice do vr_pagamentos',
        'old_pattern = r"vr_pagamentos = parse_monetary_for_calc\\(record\\[11\\]\\)"',
        'new_code = """# CORRIGIDO: Buscar vr_pagamentos na posição correta',
        '                    vr_pagamentos = 0',
        '                    if len(record) >= 15:',
        '                        try:',
        '                            vr_pagamentos = parse_monetary_for_calc(record[14])',
        '                        except:',
        '                            vr_pagamentos = parse_monetary_for_calc(record[11]) if len(record) > 11 else 0"""',
        '',
        'content = re.sub(old_pattern, new_code, content)',
        '',
        'with open("testefinal_aws_producao.py", "w") as f:',
        '    f.write(content)',
        '',
        'print("✅ Período logic fixed")',
        'EOF',
        'python3 fix_periodo.py',
        
        # 3. Verificar correções
        'echo "🔍 Verificando correções aplicadas..."',
        'grep -n "CORRIGIDO" testefinal_aws_producao.py | head -3',
        'grep -n "record\\[14\\]" testefinal_aws_producao.py | head -1',
        
        'echo "✅ Todas as correções aplicadas!"'
    ]
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': fix_commands}
    )
    
    command_id = response['Command']['CommandId']
    ssm.get_waiter('command_executed').wait(CommandId=command_id, InstanceId=instance_id)
    
    result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    
    print("📋 Resultado das correções:")
    print(result['StandardOutputContent'])
    
    if result['StandardErrorContent']:
        print("❌ Erros:")
        print(result['StandardErrorContent'])

if __name__ == "__main__":
    investigate_and_fix() 
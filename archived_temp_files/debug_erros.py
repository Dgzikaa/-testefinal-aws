#!/usr/bin/env python3
"""
Script para debugar os erros nos módulos Analítico e Tempo
Testa datas específicas para identificar quais estão com problema
"""
import subprocess
import sys
from datetime import datetime, timedelta

def testar_modulo(modulo, data_inicio, data_fim):
    """Testa um módulo específico em uma data"""
    print(f"\n🔍 Testando {modulo} para {data_inicio} - {data_fim}")
    
    try:
        cmd = [
            "python3", 
            "testefinal_aws_producao.py",
            f"--only-{modulo.lower()}",
            "--start-date", data_inicio,
            "--end-date", data_fim,
            "--verbose"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {modulo} OK para {data_inicio}")
            return True
        else:
            print(f"❌ {modulo} ERRO para {data_inicio}")
            print(f"Stderr: {result.stderr[-500:]}")  # Últimas 500 chars do erro
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {modulo} TIMEOUT para {data_inicio}")
        return False
    except Exception as e:
        print(f"❌ {modulo} EXCEÇÃO para {data_inicio}: {e}")
        return False

def main():
    """Função principal"""
    print("🔍 DEBUG - Identificando períodos com erro")
    print("=" * 50)
    
    # Gerar lista de períodos de 5 dias desde 15/02/2025
    data_inicio = datetime(2025, 2, 15)
    data_atual = datetime.now()
    
    periodos_problema = []
    
    # Testar alguns períodos específicos
    periodos_teste = []
    data_teste = data_inicio
    
    while data_teste < data_atual:
        data_fim_periodo = min(data_teste + timedelta(days=4), data_atual)
        periodos_teste.append((
            data_teste.strftime('%Y-%m-%d'),
            data_fim_periodo.strftime('%Y-%m-%d')
        ))
        data_teste = data_fim_periodo + timedelta(days=1)
    
    print(f"📊 Total de períodos para testar: {len(periodos_teste)}")
    
    # Testar módulos problemáticos
    modulos_problema = ['analitico', 'tempo']
    
    for i, (inicio, fim) in enumerate(periodos_teste):
        print(f"\n📋 Testando período {i+1}/{len(periodos_teste)}: {inicio} - {fim}")
        
        periodo_com_erro = False
        
        for modulo in modulos_problema:
            sucesso = testar_modulo(modulo, inicio, fim)
            if not sucesso:
                periodo_com_erro = True
        
        if periodo_com_erro:
            periodos_problema.append(f"{inicio} - {fim}")
            print(f"🚨 PERÍODO COM PROBLEMA: {inicio} - {fim}")
    
    # Resumo
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES")
    print("=" * 50)
    print(f"Total de períodos testados: {len(periodos_teste)}")
    print(f"Períodos com problema: {len(periodos_problema)}")
    
    if periodos_problema:
        print("\n❌ Períodos com erro:")
        for periodo in periodos_problema:
            print(f"   • {periodo}")
    else:
        print("\n✅ Nenhum período com erro encontrado nos testes")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        sys.exit(1) 
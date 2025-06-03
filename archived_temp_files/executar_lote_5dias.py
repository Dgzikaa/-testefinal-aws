#!/usr/bin/env python3
"""
Script para executar TesteFinal AWS em lote - de 5 em 5 dias
Executa todos os módulos desde 15/02/2025 até a data atual
"""
import subprocess
import sys
from datetime import datetime, timedelta
import time

def executar_testefinal(data_inicio, data_fim):
    """Executa o script principal para um período específico"""
    print(f"\n🚀 Executando TesteFinal para período: {data_inicio} até {data_fim}")
    print("=" * 70)
    
    try:
        # Comando para executar o script principal
        cmd = [
            "python3", 
            "testefinal_aws_producao.py",
            "--start-date", data_inicio,
            "--end-date", data_fim,
            "--auto"  # Modo automático
        ]
        
        print(f"📋 Comando: {' '.join(cmd)}")
        
        # Executar o comando
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min timeout
        
        if result.returncode == 0:
            print(f"✅ Sucesso para período {data_inicio} - {data_fim}")
            return True
        else:
            print(f"❌ Erro para período {data_inicio} - {data_fim}")
            print(f"Stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout para período {data_inicio} - {data_fim}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado para período {data_inicio} - {data_fim}: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 EXECUÇÃO EM LOTE - TESTEFINAL AWS")
    print("📅 Processando de 5 em 5 dias desde 15/02/2025")
    print("=" * 70)
    
    # Data de início
    data_inicio = datetime(2025, 2, 15)
    data_atual = datetime.now()
    
    # Estatísticas
    total_execucoes = 0
    execucoes_sucesso = 0
    execucoes_erro = 0
    
    # Lista para armazenar períodos com erro
    periodos_erro = []
    
    print(f"📅 Data de início: {data_inicio.strftime('%d/%m/%Y')}")
    print(f"📅 Data atual: {data_atual.strftime('%d/%m/%Y')}")
    
    # Calcular quantos períodos de 5 dias temos
    dias_total = (data_atual - data_inicio).days
    periodos_total = (dias_total // 5) + 1
    
    print(f"📊 Total de períodos de 5 dias: {periodos_total}")
    print(f"📊 Dias a processar: {dias_total}")
    
    # Confirmar execução
    resposta = input("\n❓ Deseja continuar com a execução em lote? (s/n): ")
    if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
        print("❌ Execução cancelada pelo usuário")
        return
    
    print("\n🚀 Iniciando execução em lote...")
    inicio_lote = datetime.now()
    
    # Executar para cada período de 5 dias
    data_periodo_inicio = data_inicio
    
    while data_periodo_inicio < data_atual:
        # Calcular data fim do período (5 dias depois ou data atual, o que for menor)
        data_periodo_fim = min(data_periodo_inicio + timedelta(days=4), data_atual)
        
        # Converter para strings no formato YYYY-MM-DD
        str_inicio = data_periodo_inicio.strftime('%Y-%m-%d')
        str_fim = data_periodo_fim.strftime('%Y-%m-%d')
        
        total_execucoes += 1
        
        print(f"\n📋 Execução {total_execucoes}/{periodos_total}")
        
        # Executar para este período
        sucesso = executar_testefinal(str_inicio, str_fim)
        
        if sucesso:
            execucoes_sucesso += 1
            print(f"✅ Período {str_inicio} - {str_fim} processado com sucesso")
        else:
            execucoes_erro += 1
            periodos_erro.append(f"{str_inicio} - {str_fim}")
            print(f"❌ Erro no período {str_inicio} - {str_fim}")
        
        # Avançar para o próximo período
        data_periodo_inicio = data_periodo_fim + timedelta(days=1)
        
        # Pausa entre execuções para não sobrecarregar
        if data_periodo_inicio < data_atual:
            print("⏳ Aguardando 30 segundos antes da próxima execução...")
            time.sleep(30)
    
    # Resumo final
    fim_lote = datetime.now()
    tempo_total = fim_lote - inicio_lote
    
    print("\n" + "=" * 70)
    print("📊 RESUMO DA EXECUÇÃO EM LOTE")
    print("=" * 70)
    print(f"⏱️  Tempo total: {tempo_total}")
    print(f"📋 Total de execuções: {total_execucoes}")
    print(f"✅ Sucessos: {execucoes_sucesso}")
    print(f"❌ Erros: {execucoes_erro}")
    print(f"📈 Taxa de sucesso: {(execucoes_sucesso/total_execucoes*100):.1f}%")
    
    if periodos_erro:
        print(f"\n❌ Períodos com erro:")
        for periodo in periodos_erro:
            print(f"   • {periodo}")
        
        # Perguntar se quer reprocessar os erros
        resposta = input("\n❓ Deseja reprocessar os períodos com erro? (s/n): ")
        if resposta.lower() in ['s', 'sim', 'y', 'yes']:
            print("\n🔄 Reprocessando períodos com erro...")
            
            for periodo in periodos_erro:
                inicio, fim = periodo.split(' - ')
                print(f"\n🔄 Reprocessando: {periodo}")
                sucesso = executar_testefinal(inicio, fim)
                
                if sucesso:
                    print(f"✅ Reprocessamento bem-sucedido: {periodo}")
                else:
                    print(f"❌ Reprocessamento falhou: {periodo}")
                
                time.sleep(30)  # Pausa entre reprocessamentos
    
    print(f"\n🎉 Execução em lote finalizada!")
    
    if execucoes_erro == 0:
        print("✅ Todos os períodos foram processados com sucesso!")
    else:
        print(f"⚠️  {execucoes_erro} período(s) tiveram problemas")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Execução interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        sys.exit(1) 
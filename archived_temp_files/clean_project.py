#!/usr/bin/env python3
"""
Script para limpar arquivos temporários e desnecessários do projeto TesteFinal
Mantém apenas os arquivos essenciais para produção
"""
import os
import shutil
from datetime import datetime

def clean_project():
    print("🧹 LIMPANDO PROJETO TESTEFINAL")
    print("=" * 50)
    
    # Arquivos a serem MANTIDOS (essenciais)
    keep_files = {
        # Arquivos principais de produção
        'testefinal_aws_producao.py',  # Script principal AWS
        'testefinal.py',               # Script original (backup)
        'utils.py',                    # Utilitários compartilhados
        'discord_bot.py',              # Bot Discord
        
        # Documentação importante
        'README_FINAL.md',             # Documentação principal
        'GUIA_DISCORD_BOT.md',         # Guia do Discord
        'AWS_SETUP_GUIDE.md',          # Guia de setup AWS
        
        # Arquivos de configuração
        'requirements.txt',            # Dependências Python
        'requirements_discord_bot.txt', # Dependências Discord
        
        # Infraestrutura (manter para futuras migrações)
        'deploy_aws_infrastructure.py' # Deploy da infraestrutura
    }
    
    # Arquivos temporários/teste para REMOVER
    remove_files = {
        # Scripts de upload temporários
        'upload_hybrid_version.py',
        'upload_hybrid_script.py', 
        'upload_main_file.py',
        'chunked_upload.py',
        'upload_and_setup_new_instance.py',
        
        # Scripts de fix temporários
        'fix_dependencies_and_create_hybrid.py',
        'fix_discord_test.py',
        'fix_business_metrics.py',
        'simple_fix.py',
        'fix_upload_aws.py',
        'finish_setup.py',
        
        # Scripts de teste e verificação
        'check_aws_version.py',
        'check_cron.py',
        'debug_erros.py',
        'investigate_data_structure.py',
        
        # Scripts de planilhas temporários
        'create_hybrid_spreadsheets.py',
        'create_hybrid_simple.py',
        'create_separate_spreadsheets.py',
        'clean_spreadsheet.py',
        'archive_data_safely.py',
        
        # Scripts de atualização temporários
        'update_discord_commands.py',
        'update_discord_bot.py',
        
        # Scripts de execução em lote
        'executar_lote_5dias.py'
    }
    
    # Criar pasta de arquivo se não existir
    archive_folder = "archived_temp_files"
    if not os.path.exists(archive_folder):
        os.makedirs(archive_folder)
        print(f"📁 Pasta de arquivo criada: {archive_folder}")
    
    # Estatísticas
    files_moved = 0
    files_kept = 0
    space_freed = 0
    
    # Processar todos os arquivos
    for file in os.listdir('.'):
        if os.path.isfile(file):
            file_size = os.path.getsize(file)
            
            if file in keep_files:
                print(f"✅ MANTIDO: {file} ({file_size/1024:.1f}KB)")
                files_kept += 1
            elif file in remove_files:
                # Mover para pasta de arquivo em vez de deletar
                shutil.move(file, os.path.join(archive_folder, file))
                print(f"📦 ARQUIVADO: {file} ({file_size/1024:.1f}KB)")
                files_moved += 1
                space_freed += file_size
            elif file.endswith('.py'):
                # Arquivos Python não listados - perguntar o que fazer
                print(f"❓ DESCONHECIDO: {file} ({file_size/1024:.1f}KB) - Arquivando por segurança")
                shutil.move(file, os.path.join(archive_folder, file))
                files_moved += 1
                space_freed += file_size
            else:
                print(f"ℹ️  IGNORADO: {file} ({file_size/1024:.1f}KB)")
    
    print("\n" + "=" * 50)
    print("📊 RESUMO DA LIMPEZA:")
    print("=" * 50)
    print(f"✅ Arquivos mantidos: {files_kept}")
    print(f"📦 Arquivos arquivados: {files_moved}")
    print(f"💾 Espaço organizado: {space_freed/1024:.1f}KB")
    print(f"📁 Local do arquivo: {archive_folder}/")
    
    print(f"\n🎯 PROJETO LIMPO E ORGANIZADO!")
    print("✅ Mantidos apenas arquivos essenciais para produção")
    print("📦 Arquivos temporários movidos para pasta de arquivo")
    print("🔒 Nenhum arquivo foi deletado permanentemente")
    
    # Criar arquivo de log da limpeza
    log_file = os.path.join(archive_folder, "cleanup_log.txt")
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"LIMPEZA DO PROJETO TESTEFINAL\n")
        f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write(f"Arquivos arquivados: {files_moved}\n")
        f.write(f"Espaço organizado: {space_freed/1024:.1f}KB\n\n")
        f.write("Arquivos arquivados:\n")
        for file in remove_files:
            if os.path.exists(os.path.join(archive_folder, file)):
                f.write(f"- {file}\n")
    
    print(f"📄 Log criado: {log_file}")
    
    return True

def show_final_structure():
    """Mostra a estrutura final do projeto"""
    print("\n" + "=" * 50)
    print("📁 ESTRUTURA FINAL DO PROJETO:")
    print("=" * 50)
    
    print("📂 TesteFinal/")
    for file in sorted(os.listdir('.')):
        if os.path.isfile(file):
            size = os.path.getsize(file) / 1024
            if file.endswith('.py'):
                print(f"  🐍 {file} ({size:.1f}KB)")
            elif file.endswith('.md'):
                print(f"  📄 {file} ({size:.1f}KB)")
            elif file.endswith('.txt'):
                print(f"  📝 {file} ({size:.1f}KB)")
            else:
                print(f"  📄 {file} ({size:.1f}KB)")
    
    print(f"  📁 archived_temp_files/ (arquivos temporários)")
    
    print("\n🎯 PROJETO ORGANIZADO E PRONTO PARA PRODUÇÃO!")

if __name__ == "__main__":
    if clean_project():
        show_final_structure() 
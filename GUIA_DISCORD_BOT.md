# 🤖 Guia Discord Bot - TesteFinal AWS

## 📋 **1. CRIAR BOT NO DISCORD**

### **Passo 1: Criar Aplicação**
1. Acesse: https://discord.com/developers/applications
2. Clique em **"New Application"**
3. Digite um nome: `TesteFinal Bot`
4. Clique em **"Create"**

### **Passo 2: Configurar Bot**
1. No menu lateral, clique em **"Bot"**
2. Clique em **"Add Bot"**
3. **IMPORTANTE**: Copie o **Token** (guarde com segurança!)
4. Em **"Privileged Gateway Intents"**, ative:
   - ✅ **Message Content Intent**

### **Passo 3: Convidar Bot para Servidor**
1. No menu lateral, clique em **"OAuth2"** → **"URL Generator"**
2. Em **"Scopes"**, marque: `bot`
3. Em **"Bot Permissions"**, marque:
   - ✅ **Send Messages**
   - ✅ **Use Slash Commands**
   - ✅ **Embed Links**
   - ✅ **Read Message History**
4. Copie a URL gerada e acesse no navegador
5. Selecione seu servidor e autorize

## 🔧 **2. OBTER SEU DISCORD ID**

### **Método 1: Pelo Discord**
1. Abra Discord → **Configurações** → **Avançado**
2. Ative **"Modo Desenvolvedor"**
3. Clique com botão direito no seu nome
4. Selecione **"Copiar ID"**

### **Método 2: Pelo Bot**
1. Configure o bot temporariamente com qualquer ID
2. Digite `!whoami` no chat
3. O bot retornará seu ID

## ⚙️ **3. CONFIGURAR O BOT**

### **Editar arquivo `discord_bot.py`:**
```python
# Configurações do Bot
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.EXAMPLE.TOKEN_PLACEHOLDER_DO_NOT_USE
ALLOWED_USERS = [123456789012345678]  # Substitua pelo seu Discord ID
```

### **Exemplo de configuração:**
```python
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.EXAMPLE.TOKEN_PLACEHOLDER_DO_NOT_USE
ALLOWED_USERS = [987654321098765432, 123456789012345678]  # Pode adicionar múltiplos IDs
```

## 🚀 **4. INSTALAR E EXECUTAR**

### **No EC2:**
```bash
# Conectar ao EC2
ssh -i testefinal-key.pem ec2-user@15.229.250.3

# Transferir arquivos
scp -i testefinal-key.pem discord_bot.py ec2-user@15.229.250.3:/home/ec2-user/
scp -i testefinal-key.pem requirements_discord_bot.txt ec2-user@15.229.250.3:/home/ec2-user/

# Instalar dependências
pip3.8 install --user -r requirements_discord_bot.txt

# Executar bot
python3.8 discord_bot.py
```

### **Para manter rodando sempre:**
```bash
# Instalar screen
sudo yum install screen -y

# Criar sessão permanente
screen -S discord_bot

# Executar bot
python3.8 discord_bot.py

# Desconectar (bot continua rodando)
# Pressione: Ctrl + A, depois D

# Reconectar mais tarde
screen -r discord_bot
```

## 💬 **5. COMANDOS DISPONÍVEIS**

### **📊 Comandos Básicos:**
```
!help                    # Ver todos os comandos
!status                  # Status do bot
!logs                    # Ver logs do sistema
```

### **🚀 Executar Script:**
```
!run                               # Execução padrão (dados de ontem)
!run --fixed-dates                 # Dados de teste (24/05/2025)
!run --only-analitico --fixed-dates # Só analítico com dados teste
!run --start-date 2025-05-15       # Data específica
!run --verbose                     # Logs detalhados
```

### **📋 Módulos Específicos:**
```
!run --only-analitico              # Apenas dados analíticos
!run --only-nf                     # Apenas notas fiscais
!run --only-periodo                # Apenas período
!run --only-tempo                  # Apenas tempo
!run --only-pagamentos             # Apenas pagamentos
!run --only-fatporhora             # Apenas fat/hora
```

### **🔧 Opções Avançadas:**
```
!run --no-database                 # Pular Google Sheets
!run --help                        # Ver ajuda do script
```

## 🎯 **6. EXEMPLOS DE USO**

### **Teste Rápido:**
```
!run --only-analitico --fixed-dates --verbose
```

### **Execução Completa:**
```
!run --fixed-dates
```

### **Data Específica:**
```
!run --start-date 2025-05-20 --only-analitico
```

## 🔒 **7. SEGURANÇA**

### **⚠️ IMPORTANTE:**
- ✅ **Apenas usuários autorizados** podem usar comandos
- ✅ **Token do bot** deve ser mantido **secreto**
- ✅ **IDs autorizados** controlam acesso
- ✅ **Timeout de 5 minutos** evita travamentos

### **Adicionar mais usuários:**
```python
ALLOWED_USERS = [
    123456789012345678,  # Seu ID
    987654321098765432,  # ID do colega
    555666777888999000   # ID do supervisor
]
```

## 🐛 **8. SOLUÇÃO DE PROBLEMAS**

### **Bot não responde:**
```bash
# Verificar se está rodando
screen -ls

# Ver logs em tempo real
screen -r discord_bot
```

### **Erro de permissão:**
- Verificar se seu ID está em `ALLOWED_USERS`
- Usar `!whoami` para confirmar ID

### **Erro de token:**
- Regenerar token no Discord Developer Portal
- Atualizar no arquivo `discord_bot.py`

### **Timeout de execução:**
- Script para após 5 minutos automaticamente
- Use `--only-` para testar módulos individuais

## 📱 **9. EXEMPLO DE CONVERSA**

```
Você: !status
Bot: 🤖 Status do TesteFinal Bot
     ✅ Online
     📍 AWS EC2 - São Paulo

Você: !run --only-analitico --fixed-dates
Bot: 🚀 Executando TesteFinal AWS
     ⏳ Iniciando...
     
     [Bot atualiza a mensagem com progresso]
     
     ✅ TesteFinal Executado com Sucesso!
     📊 Taxa de Sucesso: 100%
     📋 Registros: 1,303
     ⏱️ Tempo: 0:00:16
```

## 🎉 **10. RECURSOS DO BOT**

### **✅ Funcionalidades:**
- 🚀 **Execução remota** via chat
- 📊 **Relatórios em tempo real**
- 🔒 **Controle de acesso seguro**
- ⏱️ **Timeout automático**
- 📝 **Logs detalhados**
- 🎨 **Interface visual** (embeds)
- 📱 **Notificações diretas**

### **🎯 Vantagens:**
- **Conveniência**: Execute de qualquer lugar
- **Monitoramento**: Acompanhe execuções em tempo real
- **Colaboração**: Múltiplos usuários autorizados
- **Histórico**: Logs persistentes no Discord
- **Segurança**: Controle de acesso rigoroso 
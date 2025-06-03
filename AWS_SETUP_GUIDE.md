# 🚀 GUIA COMPLETO: TesteFinal na AWS

## 📋 Resumo da Solução
- **Plataforma**: AWS EC2 (São Paulo - sa-east-1)
- **Agendamento**: EventBridge (09:00 AM diário)
- **Monitoramento**: CloudWatch Dashboard + Métricas
- **Custo estimado**: $8-12/mês
- **IP**: Brasileiro (São Paulo)

## 🛠️ PRÉ-REQUISITOS

### 1. Conta AWS
- Acesso programático (Access Key + Secret Key)
- Permissões para: EC2, IAM, EventBridge, CloudWatch, SSM

### 2. Credenciais do Google Sheets
- Arquivo `service_account.json` (das configurações atuais)

### 3. Ferramentas Locais
```bash
pip install boto3 awscli
aws configure  # Configurar credenciais AWS
```

## 📦 PASSO 1: DEPLOY DA INFRAESTRUTURA

### 1.1. Execute o script de deploy:
```bash
python deploy_aws_infrastructure.py
```

**Saída esperada:**
```
🚀 Iniciando deploy da infraestrutura AWS para TesteFinal...
✅ VPC encontrada: vpc-xxxxxxxxx
✅ Security Group criado: sg-xxxxxxxxx
✅ IAM Role e Instance Profile criados
⏳ Aguardando propagação do IAM (30s)...
✅ EC2 Instance lançada: i-xxxxxxxxx
✅ Instância está running!
✅ EventBridge Rule criada
✅ CloudWatch Dashboard criado

🎉 DEPLOY CONCLUÍDO COM SUCESSO!
```

## 📤 PASSO 2: UPLOAD DAS CREDENCIAIS

### 2.1. Conectar ao EC2 via SSM (sem SSH):
```bash
# Via AWS CLI
aws ssm start-session --target i-xxxxxxxxx --region sa-east-1

# Ou via Console AWS: EC2 > Instances > Connect > Session Manager
```

### 2.2. Fazer upload do arquivo de credenciais:
**Opção A - Via SCP (se tiver SSH):**
```bash
scp service_account.json ec2-user@IP-DO-EC2:/home/ec2-user/testefinal/credentials/
```

**Opção B - Via SSM Session Manager:**
```bash
# Na sessão SSM:
sudo nano /home/ec2-user/testefinal/credentials/service_account.json
# Cole o conteúdo do arquivo e salve
```

## 🧪 PASSO 3: TESTE MANUAL

### 3.1. Testar execução via SSM:
```bash
# No console AWS ou via CLI:
aws ssm send-command \
  --instance-ids i-xxxxxxxxx \
  --document-name "TesteFinal-ExecutionDocument" \
  --region sa-east-1
```

### 3.2. Verificar logs:
```bash
# Na sessão SSM do EC2:
tail -f /home/ec2-user/testefinal/logs/execution.log
```

**Log esperado:**
```
2025-01-XX 12:00:01 - INFO - 🚀 Iniciando execução do TesteFinal na AWS EC2...
2025-01-XX 12:00:02 - INFO - 🔐 Iniciando login no ContaHub...
2025-01-XX 12:00:03 - INFO - ✅ Login no ContaHub realizado com sucesso!
2025-01-XX 12:00:04 - INFO - 📥 Buscando dados do ContaHub...
2025-01-XX 12:00:05 - INFO - ✅ 3056 registros obtidos do ContaHub
2025-01-XX 12:00:06 - INFO - 📊 Atualizando Google Sheets...
2025-01-XX 12:00:07 - INFO - ✅ Google Sheets atualizado com 3056 registros
2025-01-XX 12:00:08 - INFO - ✅ Execução concluída com sucesso em 7.45 segundos
```

## 📊 PASSO 4: MONITORAMENTO

### 4.1. CloudWatch Dashboard
- **URL**: Console AWS > CloudWatch > Dashboards > TesteFinal-Dashboard
- **Métricas disponíveis**:
  - Execuções bem-sucedidas/falhas
  - Login success/failure
  - Registros encontrados
  - Tempo de execução

### 4.2. Alarmes CloudWatch (Opcional)
```python
# Criar alarme para falhas
aws cloudwatch put-metric-alarm \
  --alarm-name "TesteFinal-ExecutionFailure" \
  --alarm-description "Alarme quando TesteFinal falha" \
  --metric-name ExecutionFailure \
  --namespace TesteFinal \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1
```

## ⏰ PASSO 5: VERIFICAR AGENDAMENTO

### 5.1. EventBridge Rules
- **Console**: EventBridge > Rules > TesteFinalDailyExecution
- **Agendamento**: `cron(0 12 * * ? *)` (09:00 AM UTC-3)
- **Status**: ENABLED

### 5.2. Histórico de Execuções
- **Console**: EventBridge > Rules > TesteFinalDailyExecution > Metrics

## 💰 CUSTOS ESTIMADOS

| Serviço | Especificação | Custo/Mês |
|---------|---------------|-------------|
| **EC2 t2.micro** | 24x7 (São Paulo) | $8.50 |
| **EBS gp2** | 8GB | $0.80 |
| **EventBridge** | 30 execuções/mês | Gratuito |
| **CloudWatch** | Métricas básicas | $1.50 |
| **Data Transfer** | Mínimo | $0.50 |
| **TOTAL** | | **~$11.30/mês** |

> **💡 DICA**: EC2 t2.micro é elegível para Free Tier (750h/mês por 12 meses)

## 🔧 MANUTENÇÃO E TROUBLESHOOTING

### Logs importantes:
```bash
# Log principal da aplicação
tail -f /home/ec2-user/testefinal/logs/execution.log

# Log do sistema EC2
sudo tail -f /var/log/messages

# Log do user-data (inicialização)
sudo tail -f /var/log/user-data.log
```

### Comandos úteis:
```bash
# Verificar status do cron
sudo systemctl status crond

# Executar manualmente
cd /home/ec2-user/testefinal
python3 aws_ec2_solution.py

# Verificar conectividade
curl -I https://sp.contahub.com
```

### Reiniciar serviços:
```bash
# Reiniciar instância
aws ec2 reboot-instances --instance-ids i-xxxxxxxxx --region sa-east-1

# Parar/Iniciar para economizar (se necessário)
aws ec2 stop-instances --instance-ids i-xxxxxxxxx --region sa-east-1
aws ec2 start-instances --instance-ids i-xxxxxxxxx --region sa-east-1
```

## 🚨 TROUBLESHOOTING COMUM

### ❌ "Login falhou"
**Possíveis causas:**
1. Credenciais incorretas
2. ContaHub indisponível
3. Problema de rede

**Soluções:**
1. Verificar credenciais no código
2. Testar conectividade: `curl -I https://sp.contahub.com`
3. Verificar logs detalhados

### ❌ "Google Sheets erro"
**Possíveis causas:**
1. Arquivo `service_account.json` ausente/inválido
2. Permissões da planilha
3. Quota da API

**Soluções:**
1. Verificar arquivo: `ls -la /home/ec2-user/testefinal/credentials/`
2. Verificar permissões da planilha
3. Verificar quota da API Google

### ❌ EventBridge não executa
**Possíveis causas:**
1. IAM permissions
2. Target incorreto
3. Instância parada

**Soluções:**
1. Verificar IAM Role permissions
2. Verificar configuração do target
3. Verificar se EC2 está running

## 📈 MELHORIAS FUTURAS

### Backup automático:
```bash
# Snapshot diário do EBS
aws ec2 create-snapshot \
  --volume-id vol-xxxxxxxxx \
  --description "TesteFinal backup $(date)"
```

### Notificações por email:
```python
# Integrar SNS para alertas por email
# Adicionar ao código: sns.publish() em casos de erro
```

### Scaling automático:
```bash
# Auto Scaling Group para alta disponibilidade
# Load Balancer para múltiplas instâncias
```

## 📞 SUPORTE

### Contatos importantes:
- **AWS Support**: Console AWS > Support
- **CloudWatch Logs**: Console AWS > CloudWatch > Log groups
- **EC2 Instance Connect**: Console AWS > EC2 > Connect

### Comandos de emergência:
```bash
# Parar execução agendada
aws events disable-rule --name TesteFinalDailyExecution --region sa-east-1

# Backup urgente dos dados
aws s3 cp /home/ec2-user/testefinal/ s3://backup-bucket/ --recursive
```

---

## ✅ CHECKLIST FINAL

- [ ] ✅ Infraestrutura AWS deployada
- [ ] ✅ Credenciais Google Sheets carregadas
- [ ] ✅ Teste manual executado com sucesso
- [ ] ✅ Dashboard CloudWatch configurado
- [ ] ✅ Agendamento EventBridge ativo
- [ ] ✅ Logs sendo gerados corretamente
- [ ] ✅ Primeira execução automática confirmada

**🎉 Parabéns! Seu TesteFinal está 100% automatizado na AWS!** 
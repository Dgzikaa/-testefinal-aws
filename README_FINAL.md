# TesteFinal AWS - Automação Completa ✅

## 📋 **RESUMO DO PROJETO**

Sistema de automação completa para extração diária de dados do ContaHub e envio para Google Sheets, executando na AWS EC2 em São Paulo.

## 🎯 **PROBLEMA RESOLVIDO**

- ❌ **Problema inicial**: Script local funcionava, mas falhava em cloud (Render, n8n)
- ✅ **Solução**: AWS EC2 em São Paulo (IP brasileiro) + URLs corretas
- 🚀 **Resultado**: 100% funcional com 6 tipos de dados diferentes

## 🏗️ **INFRAESTRUTURA AWS**

### **Recursos Criados:**
- **EC2 Instance**: `i-00b06f5201448ed61` (t3.micro, São Paulo)
- **IP Público**: `15.229.250.3`
- **Security Group**: `sg-029b998799c754c7c`
- **IAM Role**: `TesteFinalInstanceProfile`
- **EventBridge Rule**: Execução diária às 09:00 AM
- **CloudWatch Dashboard**: Monitoramento de métricas

### **Configuração:**
- **Região**: `sa-east-1` (São Paulo)
- **Sistema**: Amazon Linux 2
- **Python**: 3.8.20
- **SSH Key**: `testefinal-key.pem`

## 📊 **TIPOS DE DADOS EXTRAÍDOS**

| Tipo | Query | Registros (24/05) | Aba Google Sheets |
|------|-------|-------------------|-------------------|
| 📊 Analítico | qry=77 | 1.303 | Página1 |
| 📄 Notas Fiscais | qry=73 | 2 | Página2 |
| 📅 Período | qry=5 | 454 | Página3 |
| ⏱️ Tempo | qry=81 | 1.303 | Página4 |
| 💳 Pagamentos | qry=7 | 466 | Página24 |
| 💰 FatPorHora | qry=101 | 9 | Página5 |

## 🔧 **ARQUIVOS PRINCIPAIS**

### **Script de Produção:**
- `testefinal_aws_producao.py` - Script final para execução diária

### **Scripts AWS:**
- `deploy_aws_infrastructure.py` - Deploy da infraestrutura
- `reconectar_ec2.py` - Reconexão fácil ao EC2
- `testefinal-key.pem` - Chave SSH (privada)

### **Scripts de Teste:**
- `teste_URLs_corretas.py` - Validação das URLs corretas

## ⚙️ **CONFIGURAÇÃO INICIAL**

### **1. Credenciais AWS:**
- Access Key ID: `AWS_ACCESS_KEY_ID`
- Secret Access Key: `AWS_SECRET_ACCESS_KEY`
- Região: `sa-east-1`

### **2. Credenciais ContaHub:**
- Email: `digao@3768`
- Senha: `Geladeira@001`
- URL Login: `https://sp.contahub.com/rest/contahub.cmds.UsuarioCmd/login/17421701611337?emp=0`

### **3. Google Sheets:**
- Planilha: `Base_de_dados_CA_ordinario`
- Credenciais: `google_credentials.json` (necessário configurar no EC2)

## 🚀 **EXECUÇÃO**

### **Conectar ao EC2:**
```bash
ssh -i testefinal-key.pem ec2-user@15.229.250.3
```

### **Executar manualmente:**
```bash
cd /home/ec2-user
python3.8 testefinal_aws_producao.py
```

### **Automação:**
- EventBridge configurado para executar diariamente às 09:00 AM UTC-3
- CloudWatch monitora execução e métricas

## 📈 **MONITORAMENTO**

### **CloudWatch Metrics:**
- `TesteFinal/LoginSuccess` - Sucessos de login
- `TesteFinal/TotalRecordsProcessed` - Total de registros
- `TesteFinal/SuccessRate` - Taxa de sucesso
- `TesteFinal/ExecutionTimeSeconds` - Tempo de execução

### **Logs:**
- CloudWatch Logs Group: `/aws/ec2/testefinal`
- SSH: `tail -f /var/log/testefinal.log`

## 🔍 **DESCOBERTAS TÉCNICAS**

### **URLs Corretas (qry parameters):**
- **Problema**: Todos usavam `qry=5` → mesmos dados
- **Solução**: Cada consulta tem seu `qry` específico
- **Fonte**: Análise do `testefinal.py` original

### **IP Brasileiro:**
- **Problema**: ContaHub bloqueia IPs de datacenter/cloud internacionais
- **Solução**: AWS São Paulo (`sa-east-1`) resolve o bloqueio
- **Resultado**: Login 100% funcional

## 📝 **DEPENDÊNCIAS**

```txt
boto3>=1.26.0
requests>=2.28.0
gspread>=5.7.0
google-auth>=2.16.0
google-auth-oauthlib>=0.7.0
pandas>=1.5.0
```

## 🔒 **SEGURANÇA**

- ✅ Credenciais AWS via IAM Role (não hardcoded)
- ✅ SSH Key protegida
- ✅ Security Group restritivo
- ✅ Logs detalhados para auditoria

## 📞 **SUPORTE**

### **Problemas Comuns:**

1. **Login falha**: Verificar credenciais ContaHub
2. **Google Sheets erro**: Verificar `google_credentials.json`
3. **EC2 inacessível**: Verificar Security Group
4. **Dados diferentes**: Confirmar parâmetros `qry`

### **Comandos Úteis:**
```bash
# Verificar status EC2
aws ec2 describe-instances --instance-ids i-00b06f5201448ed61

# Logs CloudWatch
aws logs tail /aws/ec2/testefinal --follow

# Teste de conectividade
ping 15.229.250.3
```

## 🎉 **STATUS ATUAL**

✅ **SISTEMA 100% FUNCIONAL**  
✅ **Infraestrutura AWS deployada**  
✅ **Testes validados com sucesso**  
✅ **Automação configurada**  
✅ **Monitoramento ativo**  

**🚀 PRONTO PARA PRODUÇÃO!**

---
*Última atualização: 28/05/2025*
*Versão: 1.0.0 - Produção* 
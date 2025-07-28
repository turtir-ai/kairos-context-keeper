# 🚀 AWS Bedrock Free Tier Setup Guide

## 1. AWS Hesap Oluşturma
1. https://aws.amazon.com/free/ adresine git
2. "Create a Free Account" tıkla
3. Email: giye3@giyegiye.com
4. Password: Timur901!
5. Account name: Kairos-Symbiotic-AI
6. Kredi kartı bilgilerini gir (sadece doğrulama için, free tier kullanacağız)

## 2. AWS Bedrock Free Tier Aktivasyonu
1. AWS Console'a giriş yap
2. Region'u **us-east-1** (N. Virginia) seç
3. Bedrock servisine git: https://console.aws.amazon.com/bedrock/
4. "Get started" butonuna tıkla
5. Model access sekmesine git
6. Bu modelleri enable et:
   - Amazon Titan Text Express
   - Anthropic Claude 3 Haiku (en ucuz)
   - AI21 Jurassic-2 Mid

## 3. Free Tier Kotaları
- **Titan Text Express**: 10,000 input + 10,000 output tokens (ilk 30 gün)
- **Claude 3 Haiku**: 25,000 input + 25,000 output tokens (ilk 30 gün)
- **Jurassic-2**: 5,000 input + 5,000 output tokens (ilk 30 gün)

## 4. AWS CLI Credentials Setup
```bash
aws configure
# AWS Access Key ID: [IAM'den alacağız]
# AWS Secret Access Key: [IAM'den alacağız]
# Default region name: us-east-1
# Default output format: json
```

## 5. IAM User Oluşturma
1. IAM Console: https://console.aws.amazon.com/iam/
2. Users → Create user
3. Username: bedrock-mcp-user
4. Attach policies directly:
   - AmazonBedrockFullAccess
5. Create access key → Command Line Interface (CLI)
6. Access key'i kaydet

## 6. Test Komutu
```bash
aws bedrock list-foundation-models --region us-east-1
```

## 7. MCP Server Enable
MCP config'de aws-bedrock disabled: false yap ve gerçek credentials ekle.

## 🎯 Sonuç
Bu adımları takip edince AWS Bedrock MCP server'ı gerçek credentials ile çalışacak!
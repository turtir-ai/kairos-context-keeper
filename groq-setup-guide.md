# ⚡ Groq API Setup - Tamamen Ücretsiz Ultra-Hızlı LLM

## 🚀 Neden Groq?
- **Llama 3.1 70B**: 6,000 tokens/dakika ÜCRETSIZ
- **Ultra hızlı**: AWS Bedrock'tan 10x daha hızlı
- **Kredi kartı gerektirmez**: Sadece email ile kayıt
- **Production ready**: Gerçek projeler için kullanılabilir

## 📝 Adım Adım Setup

### 1. Hesap Oluşturma
1. https://console.groq.com/ adresine git
2. "Sign Up" tıkla
3. Email: giye3@giyegiye.com (veya başka email)
4. Password: Timur901!
5. Email doğrulaması yap

### 2. API Key Alma
1. Dashboard'a giriş yap
2. Sol menüden "API Keys" seç
3. "Create API Key" butonuna tıkla
4. Name: "Kairos-MCP-Server"
5. API key'i kopyala (gsk_... ile başlar)

### 3. Environment Variable Ayarlama
```bash
# Windows PowerShell
$env:GROQ_API_KEY="gsk_your_api_key_here"

# Veya .env dosyasına ekle
echo "GROQ_API_KEY=gsk_your_api_key_here" >> .env
```

### 4. MCP Server Enable Etme
`.kiro/settings/mcp.json` dosyasında:
```json
"groq-llm": {
  "disabled": false,
  "env": {
    "GROQ_API_KEY": "gsk_your_actual_api_key_here"
  }
}
```

### 5. Test Etme
```python
# Test script
python -c "
import os
os.environ['GROQ_API_KEY'] = 'your_key_here'
exec(open('groq-mcp-server.py').read())
"
```

## 🎯 Ücretsiz Kotalar
- **Llama 3.1 70B**: 6,000 tokens/dakika
- **Llama 3.1 8B**: 30,000 tokens/dakika  
- **Mixtral 8x7B**: 5,000 tokens/dakika
- **Gemma2 9B**: 15,000 tokens/dakika

## 💡 Kullanım İpuçları
- Büyük promptlar için Llama 3.1 70B kullan
- Hızlı yanıtlar için Llama 3.1 8B kullan
- Code generation için Mixtral kullan
- Rate limit aşarsan 1 dakika bekle

## 🔥 Sonuç
Bu setup ile AWS Bedrock'a ihtiyaç kalmadan ultra-hızlı LLM erişimi elde edeceksin!
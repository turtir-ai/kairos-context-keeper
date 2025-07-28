# 🆓 Ücretsiz AI/LLM Alternatifleri - AWS Bedrock Yerine

## 1. 🤗 HuggingFace Inference API (Tamamen Ücretsiz)
```python
# Ücretsiz HuggingFace API
import requests

def huggingface_generate(prompt, model="microsoft/DialoGPT-medium"):
    API_URL = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": "Bearer hf_xxxxx"}  # Ücretsiz token
    
    response = requests.post(API_URL, 
        headers=headers,
        json={"inputs": prompt}
    )
    return response.json()
```

## 2. 🌟 Groq (Çok Hızlı, Ücretsiz Kota)
- **Llama 3.1 70B**: 6,000 tokens/dakika ÜCRETSIZ
- **Mixtral 8x7B**: 5,000 tokens/dakika ÜCRETSIZ
- Kayıt: https://console.groq.com/

## 3. 🔥 Together.ai (Ücretsiz Başlangıç)
- **$25 ücretsiz kredi** yeni hesaplara
- Llama 3.1, Mixtral, Code Llama modelleri
- Kayıt: https://together.ai/

## 4. ⚡ Perplexity Labs (Sınırlı Ücretsiz)
- Günde 600 sorgu ücretsiz
- Claude 3 Haiku, Mixtral erişimi
- Web arayüzü: https://labs.perplexity.ai/

## 5. 🎯 Cohere (Ücretsiz Trial)
- Command R+ modeli
- Aylık 1000 API çağrısı ücretsiz
- Kayıt: https://cohere.com/

## 6. 🚀 Anthropic Claude (Sınırlı Ücretsiz)
- Claude 3 Haiku web arayüzü
- Günlük mesaj limiti var
- https://claude.ai/

## 7. 🔬 Google AI Studio (Gemini Ücretsiz)
- Gemini 1.5 Flash ücretsiz
- Aylık 15 requests/minute
- https://aistudio.google.com/

## 8. 🎮 Ollama (Tamamen Lokal, Ücretsiz)
```bash
# Lokal LLM çalıştırma
ollama pull llama3.1:8b
ollama run llama3.1:8b
```

## 9. 💎 OpenRouter (Çok Ucuz)
- Birçok model tek API'de
- $5 başlangıç kredisi
- https://openrouter.ai/

## 10. 🌐 Poe by Quora (Sınırlı Ücretsiz)
- Claude, GPT-4, Llama erişimi
- Günlük mesaj limiti
- https://poe.com/
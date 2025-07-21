class LLMRouter:
    def __init__(self):
        self.models = ["ollama", "gemini", "openrouter", "claude"]
    def select_model(self, task):
        # Basit seçim mantığı (geliştirilebilir)
        return self.models[0] 
import abc

class LLM(abc.ABC):
    def prompt(prompt: str) -> str:
        pass

import google.generativeai as genai
class GeminiLLM(LLM):
    _isConfigured: bool = False

    def __init__(self) -> None:
        if GeminiLLM._isConfigured:
            self.model = genai.GenerativeModel(model_name='gemini-pro')
            return
        
        with open('gemini_api_key.txt') as keyFile:
            key = keyFile.read().strip()

        genai.configure(api_key=key)
        GeminiLLM._isConfigured = True

        self.model = genai.GenerativeModel(model_name='gemini-pro')
    
    def prompt(self, prompt: str) -> str:
        return self.model.generate_content(prompt).text
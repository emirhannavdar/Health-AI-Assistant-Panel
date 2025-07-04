import os
from dotenv import load_dotenv
import google.generativeai as genai

# .env dosyasını yükle
load_dotenv()

# API anahtarını ortam değişkeninden al
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError('GEMINI_API_KEY ortam değişkeni tanımlı olmalı!')

genai.configure(api_key=GEMINI_API_KEY)

def ask_gemini(prompt, model_name="gemini-2.5-flash", temperature=0.2):
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text.strip() if hasattr(response, 'text') else str(response)
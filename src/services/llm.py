import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

# Nạp các biến môi trường từ file .env
load_dotenv()

def get_llm(temperature: float = 0.0):
    """
    Khởi tạo và trả về đối tượng LLM phù hợp.
    Nếu có biến môi trường OPENAI_API_KEY, hệ thống sẽ sử dụng ChatOpenAI (gpt-4o-mini).
    Ngược lại, hệ thống sẽ sử dụng ChatOllama với mô hình local 'qwen2.5:3b'.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("[LLM Service] Sử dụng OpenAI GPT-4o-mini.")
        return ChatOpenAI(model="gpt-4o-mini", temperature=temperature)
    else:
        print("[LLM Service] Không tìm thấy OPENAI_API_KEY. Sử dụng local model 'qwen2.5:3b' qua Ollama.")
        return ChatOllama(model="qwen2.5:3b", temperature=temperature)

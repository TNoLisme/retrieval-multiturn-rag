from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

def test_gemma_rag_pipeline():
    print("Khởi tạo model và giới hạn bộ nhớ...")
    
    # 1. Dùng OllamaLLM thay vì Ollama cũ
    # 2. Thêm num_ctx=2048 để tránh sập GGML trên máy 8GB RAM
    llm = OllamaLLM(
    model="qwen2.5:1.5b",  # Thay gemma4:e2b bằng dòng này
    temperature=0.1,
    num_ctx=2048 
)

    # 3. Tạo Prompt Template chuẩn
    template = """Bạn là một trợ lý lập trình. Dựa vào phần Ngữ cảnh (Context) được cung cấp dưới đây, hãy thực hiện yêu cầu của người dùng.

    Ngữ cảnh (Context):
    {context}

    Yêu cầu: {question}

    Trả lời:"""

    prompt = PromptTemplate(
        template=template, 
        input_variables=["context", "question"]
    )

    # 4. Tạo chuỗi xử lý (Chain)
    chain = prompt | llm

    # 5. Dữ liệu RAG giả lập
    fake_retrieved_context = """
    File: math_utils.py
    Đoạn code hiện tại:
    def calculate_total(price, tax_rate):
        return price + (price * tax_rate)
    """
    
    user_request = "Hãy rewrite hàm calculate_total trong ngữ cảnh để có thêm tính năng kiểm tra nếu price < 0 thì trả về 0."

    print("Đang xử lý RAG Prompt (Đọc context và rewrite code)...")
    
    # 6. Thực thi chain
    try:
        result = chain.invoke({
            "context": fake_retrieved_context, 
            "question": user_request
        })
        print("\n--- KẾT QUẢ REWRITE TỪ GEMMA 4 ---")
        print(result)
    except Exception as e:
        print(f"\n[LỖI]: {e}")

if __name__ == "__main__":
    test_gemma_rag_pipeline()
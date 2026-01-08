class QAEngine:
    """근거 기반 답변 생성 및 검증 전담 (지식 담당)"""
    def __init__(self, retriever, llm):
        self.retriever = retriever
        self.llm = llm

    def answer(self, question: str) -> dict:
        # 1. Retrieval (Advanced: Hybrid/Rerank)
        nodes = self.retriever.retrieve(question)
        
        # 2. Answer Generation (With Citation Instructions)
        # 3. Answer Verification (Self-Correction/Guardrail)
        # 4. Citation Formatting
        return {
            "answer": "...", 
            "sources": ["URL1", "URL2"], 
            "is_grounded": True
        }
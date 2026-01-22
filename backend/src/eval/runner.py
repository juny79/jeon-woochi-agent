class EvaluationRunner:
    """LangSmith를 통한 정량적 품질 측정"""
    def run_suite(self, dataset_name: str):
        # 1. 데이터셋 로드 (질문-정답 세트)
        # 2. QAEngine 결과 추출
        # 3. RAGAS 등 지표로 점수화 (Answer Correctness, Faithfulness)
        pass
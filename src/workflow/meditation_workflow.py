class MeditationWorkflow:
    """명상 가이드 시나리오 실행기"""
    def execute(self, mission: str):
        steps = {
            "start": "1. 조용한 장소를 찾아 결계를 칩니다.",
            "breath": "2. 단전호흡을 시작하여 기운을 모읍니다.",
            "mind": "3. 잡념을 구름처럼 흘려보냅니다.",
            "end": "4. 서서히 눈을 뜨고 현실로 돌아옵니다."
        }
        return steps
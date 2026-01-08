from openai import OpenAI # Solar는 OpenAI 호환 라이브러리 사용
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, messages: list) -> str:
        pass

class SolarClient(BaseLLMClient):
    """Upstage Solar Pro2 전용 클라이언트"""
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.upstage.ai/v1/solar"
        )
        self.model = "solar-pro"

    def generate(self, messages: list) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"허허, 기운(API)이 원활하지 않구려: {str(e)}"
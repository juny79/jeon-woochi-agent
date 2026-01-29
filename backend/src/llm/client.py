from openai import OpenAI
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, messages: list) -> str:
        pass

    @abstractmethod
    def stream_generate(self, messages: list):
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
            print(f"   [LLM] Solar API 호출 중... (메시지: {len(messages)}개)")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7
            )
            result = response.choices[0].message.content
            print(f"   [LLM] 응답 받음: {len(result)}자")
            return result
        except Exception as e:
            print(f"   [LLM] API 오류: {str(e)}")
            return f"허허, 기운(API)이 원활하지 않구려: {str(e)}"

    def stream_generate(self, messages: list):
        """스트리밍 응답 생성을 위한 제너레이터"""
        try:
            print(f"   [LLM] Solar API 스트리밍 호출 중... (메시지: {len(messages)}개)")
            print(f"   [LLM] 시스템 메시지: {messages[0]['content'][:100]}...")
            print(f"   [LLM] 사용자 메시지 길이: {len(messages[-1]['content'])}자")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                stream=True
            )
            
            chunk_index = 0
            for chunk in response:
                chunk_index += 1
                try:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta and hasattr(delta, 'content') and delta.content:
                            content = delta.content
                            if chunk_index <= 5:
                                print(f"   [LLM] 첫 청크: {repr(content[:50])}")
                            yield content
                except Exception as chunk_error:
                    print(f"   [LLM] 청크 {chunk_index} 처리 오류: {str(chunk_error)}")
                    continue
            
            print(f"   [LLM] 스트리밍 완료. 총 {chunk_index}개 청크")
        except Exception as e:
            print(f"   [LLM] API 스트리밍 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            yield f"\n허허, 기운(API)이 갑자기 끊겼구려: {str(e)}"

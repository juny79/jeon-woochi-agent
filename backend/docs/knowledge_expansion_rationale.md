# 📎 knowledge.md 확장 전략 보고서 — 작성 근거 및 기술적 판단 설명

**작성일**: 2026년 3월 26일  
**참고 보고서**: `backend/docs/knowledge_expansion_strategy.md`  
**목적**: 확장 전략 보고서의 각 항목이 어떤 코드적·기술적 근거에서 도출되었는지 명확히 설명

---

## 개요

확장 전략 보고서의 모든 항목은 **추상적인 이론이 아니라 현재 코드베이스에서 직접 확인한 수치와 구조**에서 도출되었다. 본 문서는 근거 코드를 인용하며 각 판단의 출처를 설명한다.

---

## 근거 1 — "청크 1~2개" 문제 진단

### 근거 코드

```python
# backend/src/config.py
CHUNK_SIZE = 500       # 문서를 500자 단위로 자름
CHUNK_OVERLAP = 50     # 문맥 유지를 위해 50자씩 겹치게 자름
```

### 판단 과정

현재 `knowledge.md`의 실제 분량은 약 **700자** (5개 섹션)이다.  
`CHUNK_SIZE = 500`이면 700자 문서는 다음과 같이 분리된다.

```
청크 1: 0~500자   (섹션 1~4 대부분 포함)
청크 2: 450~700자 (오버랩 50자 포함, 섹션 4~5)
```

즉 문서 전체가 **1~2개의 청크로 수렴**된다.

### 이것이 문제인 이유

RAG 시스템은 사용자 질문과 가장 유사한 청크를 검색하여 LLM에 전달한다.  
청크가 1~2개이면 어떤 질문을 하든 **항상 같은 결과**가 반환되어 검색 자체가 무의미해진다.

```
"업보가 뭐야?"  ──┐
"호흡법 알려줘" ──┤──→ 항상 청크 1번 반환 (모든 주제 혼재)
"선도가 뭐야?"  ──┘
```

검색이 차별화되지 않으면 BM25나 Vector Search를 구성하는 의미도 사라진다.

---

## 근거 2 — "1섹션 = 1주제" RAG 구조 원칙

### 근거: 파이프라인 동작 방식

```
사용자 질문
    ↓
HybridRetriever.retrieve(query)
    → 상위 k개 청크 반환
    ↓
QAEngine.get_answer()
    → 청크들을 [비급서 1권], [비급서 2권]... 으로 조립
    → LLM에 전달
    ↓
LLM은 "전달된 컨텍스트 안에서만" 답변 생성
```

### 컨텍스트 오염(Context Pollution) 문제

```python
# backend/src/qa/engine.py
context_parts = []
for i, doc in enumerate(retrieved_docs):
    context_parts.append(f"[비급서 {i+1}권]: {doc.page_content}")

context_text = "\n\n".join(context_parts)
```

LLM은 `context_text` 전체를 받아서 답변한다.  
한 청크 안에 여러 주제가 혼재하면 LLM이 **질문과 관련 없는 정보도 컨텍스트로 받아** 답변이 흐트러진다.

**예시:**

```
❌ 현재 — 청크 1개에 3가지 주제 혼재:
[비급서 1권]: 환생은 육신이 소멸해도... 도교의 무위자연은...
               업보(Karma)는 자신이 내보낸 에너지가...

사용자: "업보가 뭐야?"
→ LLM 컨텍스트에 환생·도교·업보 모두 유입
→ 답변에 관련 없는 내용 혼재 위험

✅ 권장 — 주제별 독립 청크:
[비급서 1권]: 업(業)이란 자신이 내보낸 의도와 행동의 에너지가...

사용자: "업보가 뭐야?"
→ LLM 컨텍스트에 업보 내용만 집중 전달
→ 핵심 답변 생성
```

### 결론

문서 구조와 RAG 검색 품질은 **직접 연결**되어 있다.  
1섹션 = 1주제 원칙은 LLM에 전달되는 컨텍스트의 **신호 대 잡음비(Signal-to-Noise Ratio)**를 높이는 가장 기본적인 설계 원칙이다.

---

## 근거 3 — 우선순위 A/B/C 분류 기준

### 우선순위 A (수행법 & 장애물): 명상 앱의 본질적 기능

명상 챗봇에게 사용자가 가장 먼저 묻는 것은 **"어떻게 하면 돼요?"** 류의 실용적 질문이다.  
현재 `knowledge.md`에는 "단전호흡"을 단 한 문장으로만 언급하고,  
단계별 수행법이나 "잡념이 계속 와요", "졸려요"와 같은 현실적 장애물에 대한 내용이 **전혀 없다.**  

이 공백을 먼저 채우지 않으면 에이전트의 핵심 기능이 작동하지 않는다.

### 우선순위 B (한국 전통 수행): 페르소나와 지식의 불일치 해소

```python
# backend/src/agent/persona_prompt.py 의도
# 전우치는 "조선의 도사"이자 "명상과 영혼의 전문가"

# backend/src/qa/engine.py
prompt = [
    {"role": "system", "content": (
        "당신은 명상과 영혼의 전문가 '전우치'요. "
        "아래 제공된 [참고한 비급서]의 내용을 바탕으로 질문에 답하시오."  # ← 핵심
    )},
    ...
]
```

전우치는 **비급서의 내용에 근거해서만** 답한다. 그런데 현재 비급서(knowledge.md)에는  
선도, 단학, 기공 등 **"도사 전우치"가 당연히 알아야 할 한국 전통 수행 내용이 하나도 없다.**  

페르소나는 "조선 도사"인데 지식은 "일반 명상 입문서"인 불일치 상태다.  
이 격차를 B 우선순위로 분류하여 조기에 해소하는 것이 페르소나 일관성을 위해 필수적이다.

### 우선순위 C (철학·생활 응용): 심화 사용자 대상

A와 B가 충족된 이후, 더 깊은 탐구를 원하는 사용자를 위한 콘텐츠다.  
당장 답변 품질과 직결되지는 않아 C로 분류했다.

---

## 근거 4 — `heading` 전략으로의 전환 권장

### 근거 코드

```python
# backend/src/processor/chunker_factory.py

elif strategy == "recursive":
    # chunk_size 기준으로 글자수를 세어 자름
    return RecursiveCharacterTextSplitter(
        chunk_size=Config.CHUNK_SIZE,    # 500자
        chunk_overlap=Config.CHUNK_OVERLAP  # 50자
    )

elif strategy == "heading":
    # 마크다운 헤딩 기호를 우선 분할 기준으로 사용
    return RecursiveCharacterTextSplitter(
        separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", " "]
    )
```

### 두 전략의 차이

| | `recursive` | `heading` |
|---|---|---|
| **분할 기준** | 글자 수 (500자) | 마크다운 헤딩 (`##`, `###`) |
| **장점** | 분량이 균일한 청크 생성 | 주제 단위로 의미 있는 청크 생성 |
| **단점** | 문단 중간에서 끊길 수 있음 | 섹션별 분량이 불균일할 수 있음 |
| **최적 대상** | 비구조화 텍스트 | 구조화된 마크다운 문서 |

확장된 `knowledge.md`는 "1섹션 = 1주제" 원칙에 따라 H2/H3 계층으로 구조화된다.  
**헤딩 경계에서 자르는 `heading` 전략이 이 구조에 가장 자연스럽게 맞는다.**

`recursive` 전략은 500자가 넘는 섹션을 문장 중간에서 잘라,  
"단전호흡의 3단계: 역복식호흡"과 같은 내용이 두 청크에 걸쳐 불완전하게 분리될 수 있다.

---

## 근거 5 — 키워드 밀도 확보 (BM25 검색 강화)

### 근거 코드

```python
# backend/src/retriever/hybrid_retriever.py
EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.5, 0.5],   # ← BM25와 Vector의 가중치가 동일
)
```

### BM25 알고리즘의 작동 원리

BM25는 **쿼리 토큰이 문서에 얼마나 자주, 집중되어 등장하는지**로 점수를 계산한다.  
이 시스템에서 BM25는 Vector와 동일한 0.5 가중치를 가지므로, BM25 검색 품질이 낮으면  
최종 검색 정확도가 절반 수준으로 저하된다.

**예시:**

```
사용자 쿼리: "단전호흡"
BM25 토큰화: ["단전호흡"]

현재 knowledge.md: "단전호흡"이 1회 등장 → BM25 점수 낮음
                   → 벡터 검색만 유효한 상황

확장 후 (권장): "단전호흡"이 섹션 제목, 본문, 단계 설명에 반복 등장
               → BM25 점수 상승 → 하이브리드 검색 효과 극대화
```

각 섹션에서 해당 주제의 **핵심 키워드를 자연스럽게 2~3회 이상 반복**하는 것이  
BM25의 50% 가중치를 제대로 활용하는 방법이다.

---

## 근거 6 — 크롤러 + 증류 파이프라인 활성화 제안

### 근거 코드

```python
# backend/main.py — 구현은 완료되어 있으나 실제로 미활용 중

def distill_knowledge(docs):
    """수집된 날것의 정보를 전우치 말투와 비급서 형태로 변환"""
    client = SolarClient(api_key=Config.SOLAR_API_KEY)
    
    for doc in docs:
        prompt = [
            {"role": "system", "content": (
                "당신은 조선의 도사 '전우치'이오. 아래 [Raw Data]를 읽고, "
                "'전우치의 비급' 형태로 재구성하시오..."
            )},
            {"role": "user", "content": f"[Raw Data]\n{doc.page_content}"}
        ]
        distilled_content = client.generate(prompt)
        ...

# run_ingest() 함수 내:
crawler = MeditationNewsCrawler()
news_docs = crawler.fetch_data(query="기초 명상 및 건강관리")

if news_docs:
    distilled_news = distill_knowledge(news_docs)   # ← 이 줄이 이미 존재함
    all_docs.extend(distilled_news)
```

### 판단

이 파이프라인은 새롭게 개발이 필요한 기능이 아니라 **이미 완성된 코드**다.  
현재 작동하지 않는 이유는 `MeditationNewsCrawler`의 실제 수집 대상 URL과  
쿼리 목록이 채워지지 않았기 때문이다.

> **코드 인프라는 있다 → URL 목록과 쿼리만 추가하면 즉시 동작**

외부 전문 자료를 수동으로 작성하는 대신 이 파이프라인을 활성화하면,  
LLM이 자동으로 전우치 어투로 변환한 콘텐츠를 지속적으로 누적할 수 있다.

---

## 전체 근거 출처 요약

| 보고서 항목 | 근거 파일 | 근거 내용 |
|-----------|---------|---------|
| "청크 1~2개" 문제 | `src/config.py` | `CHUNK_SIZE = 500` + `knowledge.md` 실 분량 700자 |
| 1섹션 = 1주제 원칙 | `src/qa/engine.py` | 청크가 그대로 LLM 컨텍스트로 전달되는 구조 |
| 우선순위 A (수행법) | `data/knowledge.md` | 단계별 수행법 섹션 전무 확인 |
| 우선순위 B (전통 수행) | `src/agent/persona_prompt.py` | "조선 도사" 페르소나 vs 지식 불일치 |
| `heading` 전략 권장 | `src/processor/chunker_factory.py` | heading 전략의 separator 분석 |
| 키워드 밀도 강조 | `src/retriever/hybrid_retriever.py` | BM25 : Vector = 0.5 : 0.5 동일 가중치 |
| 크롤러 파이프라인 활성화 | `main.py` | `distill_knowledge()` 구현 완료 상태 확인 |

---

**작성**: GitHub Copilot  
**연관 문서**: `backend/docs/knowledge_expansion_strategy.md`  
**코드 기준 버전**: 2026년 3월 26일 기준 `main` 브랜치

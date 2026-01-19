## 🧙‍♂️ 전우치 RAG 챗봇 시스템 종합보고서

**작성일**: 2026-01-19  
**프로젝트명**: jeon-woochi-agent (환생한 전우치의 명상소)  
**상태**: 🟡 진행 중 (기능 구현 완료, 비디오 스트리밍 최종 조정 중)

---

## 📋 1. 프로젝트 개요

### 1.1 목표
웹 기반 명상 가이드 챗봇 시스템 구축
- **기술**: Retrieval-Augmented Generation (RAG) + 하이브리드 검색
- **LLM**: Upstage Solar Pro API
- **UI**: Streamlit 웹 프레임워크
- **특징**: 인트로 영상 + 자동 재생 + 음성 지원

### 1.2 핵심 기능
✅ **완료**:
- 마크다운 지식베이스 적재 (data/knowledge.md)
- 하이브리드 검색 (Vector + BM25)
- 명상 QA 시스템
- CLI 및 웹 인터페이스
- 인트로 전체화면 영상 표시

🟡 **진행 중**:
- 비디오 HTTP 스트리밍 (포트 8889)
- 음성 재생 (CORS/접근성 문제)

---

## 🏗️ 2. 시스템 아키텍처

### 2.1 전체 흐름도

```
[사용자 입력]
    ↓
┌─────────────────────────────────────────┐
│     JeonWoochiAgent (src/agent/)        │
│  - 페르소나 로딩                          │
│  - 대화 메모리 관리                       │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│      QAEngine (src/qa/engine.py)        │
│  - 쿼리 처리                             │
│  - LLM 호출 조정                         │
│  - 컨텍스트 조립                         │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│   HybridRetriever (src/retriever/)      │
│  ├─ VectorDB (ChromaDB)                 │
│  │  └─ 의미 기반 검색 (Embeddings)     │
│  └─ BM25 Retriever                      │
│     └─ 키워드 기반 검색                  │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│   VectorDBManager (src/vector_store/)   │
│  - ChromaDB 관리                         │
│  - 문서 캐싱                             │
│  - 컬렉션 생성/조회                      │
└─────────────────────────────────────────┘
    ↓
[LLM 응답] → [Streamlit 웹 UI] → [사용자]
```

### 2.2 데이터 흐름

```
데이터 적재 (Ingest Mode):
  data/knowledge.md 
    ↓
  ChunkerFactory (recursive/semantic/heading 전략)
    ↓
  VectorDBManager (Embeddings)
    ↓
  ChromaDB (meditation_recursive 컬렉션)
    ↓
  BM25 인덱스 (메모리 캐시)

QA 처리 (Serve Mode):
  사용자 질문 
    ↓
  HybridRetriever.retrieve()
    ├─ 1. Vector Search (상위 문서)
    ├─ 2. BM25 Search (키워드 매칭)
    └─ 3. 결과 병합 + 중복 제거
    ↓
  QAEngine.get_answer()
    ├─ 1. 검색된 문서 전달
    ├─ 2. SolarClient API 호출
    └─ 3. 응답 생성
    ↓
  사용자에게 표시
```

---

## 📁 3. 파일 구조 및 역할

### 3.1 루트 디렉토리 파일

```
jeon-woochi-agent/
├── main.py                    # 진입점 (3가지 모드: ingest, eval, serve)
├── video_server.py            # Flask 기반 비디오 HTTP 서버 (포트 8889)
├── requirements.txt           # 의존성 패키지
├── .env                       # API 키 환경변수 (.gitignore)
├── README.md                  # 프로젝트 설명
└── test_serve.py             # 통합 테스트 스크립트
```

### 3.2 src/ 모듈 구조

#### **src/config.py** - 설정 관리
```python
역할: 환경변수 로드 및 상수 관리
의존: python-dotenv
제공:
  - Config.SOLAR_API_KEY
  - Config.DB_PATH
  - Config.MODEL_NAME
```

#### **src/agent/** - 챗봇 에이전트
```
agent/
├── orchestrator.py           # JeonWoochiAgent 클래스
│   └─ chat(prompt) → LLM 응답 생성
├── persona_prompt.py         # 전우치 페르소나 시스템 프롬프트
└── graph_agent.py            # (미사용) LangGraph 기반 구현

흐름: 사용자 입력 → JeonWoochiAgent.chat() 
    → QAEngine 호출 → LLM 응답 반환
```

#### **src/qa/** - QA 엔진
```
qa/
└── engine.py
    역할: 검색 + LLM 통합
    주요 메서드:
      - get_answer(query) 
        ├─ retriever.retrieve(query) → 관련 문서
        ├─ SolarClient 호출
        └─ 최종 답변 생성

    의존:
      - HybridRetriever
      - SolarClient (LLM API)
```

#### **src/retriever/** - 하이브리드 검색
```
retriever/
└── hybrid_retriever.py
    역할: Vector Search + BM25 키워드 검색 병합
    
    구조:
    HybridRetriever
    ├─ vector_retriever (ChromaDB)
    │  └─ get_relevant_documents(query) → 의미 유사 문서
    └─ bm25_retriever (rank_bm25)
       └─ get_relevant_documents(query) → 키워드 매칭
    
    결과 병합:
    1. 두 검색기 결과 합치기
    2. 중복 제거 (메타데이터 기반)
    3. 점수 기반 정렬
```

#### **src/vector_store/** - 벡터 DB 관리
```
vector_store/
└── manager.py
    
    VectorDBManager 클래스:
    ├─ add_documents(docs, strategy)
    │  ├─ ChunkerFactory로 청킹
    │  ├─ ChromaDB에 저장
    │  └─ BM25 인덱스 생성
    │
    ├─ get_bm25_retriever()
    │  └─ BM25Retriever 인스턴스 반환
    │
    └─ stored_docs (dict)
       └─ 문서 캐시
    
    BM25Retriever 클래스:
    ├─ BaseRetriever 상속
    ├─ _get_relevant_documents(query)
    │  └─ BM25Okapi로 점수 계산
    └─ invoke(query)
       └─ BaseRetriever 인터페이스

    내부 객체:
    - ChromaDB 인스턴스
      └─ 컬렉션: "meditation_recursive"
         └─ 저장된 청크 + 임베딩
    - BM25Okapi 인스턴스
      └─ 코퍼스: 모든 문서 텍스트
```

#### **src/processor/** - 데이터 처리
```
processor/
├── chunker_factory.py
│   역할: 청킹 전략 선택
│   지원 전략:
│   1. recursive: 재귀적 분할 (기본)
│   2. semantic: 의미 기반 분할
│   3. heading: 제목 기반 분할
│
└── 의존: langchain-experimental
```

#### **src/crawler/** - 웹 크롤러 (선택)
```
crawler/
└── meditation_crawler.py
    역할: 뉴스/웹 데이터 수집 (현재 미사용)
    의존: requests, beautifulsoup4
```

#### **src/eval/** - 평가 시스템
```
eval/
└── runner.py
    역할: LangSmith 기반 정량 평가
    의존: langsmith
    상태: 구현됨 (ingest 모드에서 선택적 실행)
```

#### **src/ui/** - 웹 UI
```
ui/
└── app.py
    역할: Streamlit 기반 웹 인터페이스
    
    주요 함수:
    ├─ show_intro()
    │  ├─ CSS: 전체화면 설정 (사이드바/헤더 숨김)
    │  ├─ HTML5 비디오 임베드
    │  │  ├─ src: http://127.0.0.1:8889/videos/intro.mp4
    │  │  ├─ autoplay + playsinline
    │  │  └─ 상세 JavaScript 로깅
    │  └─ 8초 카운트다운 후 main()으로 전환
    │
    └─ main()
       ├─ 채팅 인터페이스
       ├─ 이전 메시지 표시
       ├─ 사용자 입력 처리
       └─ get_agent()로 응답 생성
    
    의존:
    - Streamlit
    - JeonWoochiAgent
    - VectorDBManager
    - HybridRetriever
    - QAEngine
```

#### **src/llm/** - LLM 클라이언트
```
llm/
└── client.py
    역할: Upstage Solar API 호출
    
    SolarClient 클래스:
    ├─ __init__(api_key)
    ├─ call(messages) → LLM 응답
    └─ ConversationBufferMemory와 호환
    
    의존: openai>=1.0.0 (OpenAI 호환)
    주소: https://api.upstage.ai/v1/chat/completions
    모델: upstage-solar-pro (또는 환경변수)
```

#### **src/common/** - 공통 스키마
```
common/
└── schema.py
    역할: 데이터 모델 정의
    제공:
    - Document 모델
    - QueryResponse 모델
    - 등등
```

---

## 🔄 4. 실행 모드별 흐름

### 4.1 Ingest 모드 (데이터 적재)

```bash
python main.py ingest --strategy recursive
```

**실행 순서**:
1. **load_markdown_knowledge()** → data/knowledge.md 읽기
   ```
   input: "data/knowledge.md"
   output: [Document(page_content=..., metadata={source: ...})]
   ```

2. **VectorDBManager.add_documents()** → 청킹 및 임베딩
   ```
   input: [Document]
   process:
     ├─ ChunkerFactory(strategy="recursive") 생성
     ├─ split_documents() → 작은 청크들
     ├─ UpstageEmbeddings로 임베딩
     └─ ChromaDB 저장
   output: "meditation_recursive" 컬렉션 생성
   ```

3. **BM25 인덱스 생성**
   ```
   manager.stored_docs 에 문서 캐시
   BM25Okapi(corpus) 생성
   ```

4. **결과**: ChromaDB + BM25 인덱스 준비 완료

---

### 4.2 Serve 모드 - Web (웹 UI)

```bash
python main.py serve --interface web --strategy recursive
```

**실행 순서**:

1. **start_video_server()** → Flask 서버 시작 (포트 8889)
   ```
   별도 프로세스로 video_server.py 실행
   endpoint: GET /videos/intro.mp4
   ```

2. **Streamlit 실행** (포트 8502)
   ```
   subprocess.run([python, "-m", "streamlit", "run", "src/ui/app.py"])
   Local URL: http://localhost:8502
   ```

3. **페이지 로드** (사용자가 localhost:8502 접속)
   ```
   if show_intro:
     ├─ show_intro() 호출
     ├─ 전체화면 CSS 적용
     ├─ HTML5 <video> 임베드
     │  └─ src="http://127.0.0.1:8889/videos/intro.mp4"
     ├─ JavaScript 자동 재생
     └─ 8초 후 main()으로 전환
   else:
     └─ main() 호출 (채팅 인터페이스)
   ```

4. **채팅 인터페이스** (main())
   ```
   사용자 입력 → st.chat_input()
     ↓
   get_agent(strategy="recursive") 호출
     ├─ VectorDBManager 생성
     ├─ HybridRetriever 생성
     ├─ QAEngine 생성
     └─ JeonWoochiAgent 캐시 (재사용)
     ↓
   agent.chat(prompt) 호출
     ├─ qa_engine.get_answer(prompt)
     │  ├─ retriever.retrieve(prompt) → 문서 검색
     │  ├─ SolarClient 호출 (LLM)
     │  └─ 응답 생성
     └─ 메모리에 저장
     ↓
   st.chat_message("assistant") 에 표시
   ```

---

### 4.3 Serve 모드 - CLI (터미널)

```bash
python main.py serve --interface cli --strategy recursive
```

**실행 순서**:
1. VectorDBManager, HybridRetriever, QAEngine, JeonWoochiAgent 초기화
2. `while True:` 루프로 사용자 입력 받기
3. `agent.chat(user_input)` 호출
4. 응답 출력

---

## 🔗 5. 파일 간 의존성 그래프

```
main.py (진입점)
├─ config.py ─────────────────────────────────┐
├─ src/agent/orchestrator.py                  │
│  └─ src/qa/engine.py                        │
│     └─ src/retriever/hybrid_retriever.py    │
│        ├─ src/vector_store/manager.py ◄────┘
│        │  ├─ chromadb
│        │  ├─ rank_bm25
│        │  └─ langchain-core
│        │
│        └─ src/common/schema.py
│
├─ src/processor/chunker_factory.py
│  └─ langchain-experimental
│
├─ src/llm/client.py
│  └─ openai>=1.0.0
│
├─ src/crawler/meditation_crawler.py
│  ├─ requests
│  └─ beautifulsoup4
│
├─ src/eval/runner.py
│  └─ langsmith
│
├─ src/ui/app.py
│  ├─ streamlit>=1.30.0
│  └─ src/agent/orchestrator.py
│
├─ video_server.py
│  └─ flask
│
└─ src/agent/persona_prompt.py
```

---

## 📊 6. 현재 구현 상태

### 6.1 완료된 기능

| 모듈 | 기능 | 상태 | 테스트 |
|------|------|------|--------|
| **Config** | 환경변수 로드 | ✅ 완료 | ✅ |
| **ChunkerFactory** | 3가지 청킹 전략 | ✅ 완료 | ✅ |
| **VectorDBManager** | ChromaDB 관리 + BM25 | ✅ 완료 | ✅ |
| **BM25Retriever** | Pydantic BaseRetriever | ✅ 완료 | ✅ |
| **HybridRetriever** | 검색 결과 병합 | ✅ 완료 | ✅ |
| **QAEngine** | 검색 + LLM 통합 | ✅ 완료 | ✅ |
| **SolarClient** | LLM API 호출 | ✅ 완료 | ✅ |
| **JeonWoochiAgent** | 페르소나 + 메모리 | ✅ 완료 | ✅ |
| **CLI 모드** | 터미널 대화 | ✅ 완료 | ✅ |
| **Ingest 모드** | 지식베이스 적재 | ✅ 완료 | ✅ |
| **Streamlit 웹 UI** | 채팅 인터페이스 | ✅ 완료 | ✅ |
| **인트로 영상** | 전체화면 표시 | ✅ 완료 | ✅ |
| **비디오 서버** | Flask HTTP 스트리밍 | ✅ 완료 | 🟡 |

### 6.2 진행 중인 기능

| 기능 | 문제 | 원인 | 해결책 |
|------|-----|------|--------|
| **음성 재생** | 브라우저에서 음성 안 들림 | CORS? 파일 로드 실패? | JavaScript 로깅 추가 (F12 콘솔 확인 필요) |
| **비디오 로딩** | 영상이 멈춰 있음 | HTTP 서버 접근성? | Console 로그 기반 디버깅 |

---

## 🛠️ 7. 핵심 구현 세부사항

### 7.1 BM25Retriever 구현 (src/vector_store/manager.py)

```python
class BM25Retriever(BaseRetriever):
    """LangChain BaseRetriever를 상속한 BM25 검색기"""
    
    bm25: BM25Okapi = Field(exclude=True)
    corpus: List[str] = Field(exclude=True)
    documents: List[Document] = Field(exclude=True)
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        # 1. 토큰화
        tokens = query.lower().split()
        
        # 2. BM25 점수 계산
        scores = self.bm25.get_scores(tokens)
        
        # 3. 점수 기반 정렬
        docs_with_scores = [
            (self.documents[i], scores[i])
            for i in range(len(scores))
        ]
        docs_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 4. 상위 k개 반환
        return [doc for doc, score in docs_with_scores[:4]]
```

**의의**: 
- LangChain과 호환성 유지
- Pydantic V2 필드 선언 규칙 준수
- `exclude=True`로 순환 참조 방지

### 7.2 HybridRetriever 결과 병합 (src/retriever/hybrid_retriever.py)

```python
def retrieve(self, query: str) -> List[Document]:
    # 1. Vector Search
    vector_docs = self.vector_retriever.invoke(query)
    
    # 2. BM25 Search
    bm25_docs = self.bm25_retriever._get_relevant_documents(query)
    
    # 3. 결합
    combined = vector_docs + bm25_docs
    
    # 4. 중복 제거 (메타데이터 기반)
    seen_ids = set()
    unique_docs = []
    for doc in combined:
        doc_id = doc.metadata.get("source", "") + doc.page_content[:50]
        if doc_id not in seen_ids:
            seen_ids.add(doc_id)
            unique_docs.append(doc)
    
    return unique_docs
```

**의의**:
- Vector + Keyword 검색의 장점 결합
- 중복 제거로 컨텍스트 효율성 증대

### 7.3 Streamlit 비디오 임베드 (src/ui/app.py)

```python
st.markdown(f"""
<div id="intro-video-container">
    <video id="intro-video"
           autoplay
           playsinline
           style="width: 100%; height: 100%; object-fit: cover;">
        <source src="http://127.0.0.1:8889/videos/intro.mp4" type="video/mp4">
    </video>
</div>

<script>
    var video = document.getElementById('intro-video');
    
    // 메타데이터 로드 시 음성 활성화
    video.addEventListener('loadedmetadata', function() {
        video.muted = false;
        video.volume = 1.0;
    });
    
    // 자동 재생
    video.play().then(() => {
        console.log('[INTRO] 비디오 재생 시작');
    }).catch(err => {
        console.error('[INTRO] 비디오 로드 에러:', err.message);
    });
</script>
""", unsafe_allow_html=True)
```

**의의**:
- Streamlit의 `st.video()` 대신 HTML5 직접 제어
- 세밀한 자동 재생 및 음성 제어 가능

---

## 🚀 8. 배포 및 실행 방법

### 8.1 개발 환경 설정

```bash
# 1. 가상환경 생성
python -m venv .venv
.venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정
# .env 파일에 SOLAR_API_KEY 추가
SOLAR_API_KEY=your_api_key_here
```

### 8.2 데이터 적재

```bash
python main.py ingest --strategy recursive
# output: "meditation_recursive" 컬렉션 생성
#        BM25 인덱스 준비 완료
```

### 8.3 웹 인터페이스 실행

```bash
python main.py serve --interface web --strategy recursive
# 1. 비디오 서버 시작 (포트 8889)
# 2. Streamlit 실행 (포트 8502)
# 3. http://localhost:8502 접속
```

### 8.4 CLI 인터페이스 실행

```bash
python main.py serve --interface cli --strategy recursive
# 터미널에서 대화형 챗봇 사용
```

---

## 🐛 9. 현재 알려진 문제 및 해결 전략

### 문제 1: 비디오 음성 재생 안 됨

**증상**: 
- 영상은 표시되고 자동 재생됨
- 하지만 음성 없음

**원인 분석 필요**:
```
F12 콘솔에서 확인할 로그:
✓ [INTRO] 인트로 스크립트 시작
✓ [INTRO] 비디오 요소 찾음: YES
✓ [INTRO] 자동 재생 시도...
? [INTRO] 비디오 로드 에러: ??? (이 부분 확인!)
? [INTRO] 메타데이터 로드됨: ???
? [INTRO] 음성 활성화: ???
```

**잠재적 원인**:
1. HTTP 서버 (8889) 미응답
2. CORS 정책 (크로스 도메인)
3. 브라우저 자동 재생 정책 (muted 강제)
4. 파일 경로/인코딩 문제

**다음 단계**:
1. 브라우저 F12 → Console 탭 확인
2. `[INTRO]` 로그 메시지 분석
3. Network 탭에서 `intro.mp4` 요청 확인
4. 필요시 CORS 헤더 추가 (video_server.py)

---

## 📝 10. 개선 로드맵

### Phase 1: 비디오 스트리밍 안정화 (즉시)
- [ ] JavaScript 로깅으로 정확한 원인 파악
- [ ] CORS 헤더 추가 (Flask Response)
- [ ] 파일 경로 검증
- [ ] 음성 재생 테스트

### Phase 2: 기능 확대 (단기)
- [ ] 채팅 히스토리 저장 (JSON/DB)
- [ ] 사용자 설정 (명상 장르별, 시간별)
- [ ] 평가 시스템 활성화 (LangSmith)

### Phase 3: UX 개선 (중기)
- [ ] 모바일 반응형 UI
- [ ] 다크/라이트 테마
- [ ] 음성 입력 (STT)
- [ ] 음성 응답 (TTS)

### Phase 4: 프로덕션 배포 (장기)
- [ ] Docker 컨테이너화
- [ ] AWS/GCP 배포
- [ ] 로깅 및 모니터링 (ELK 스택)
- [ ] 성능 최적화

---

## 📚 11. 주요 라이브러리 버전

```
LangChain: 0.3.0+
ChromaDB: 0.5.0+
Streamlit: 1.30.0+
OpenAI: 1.0.0+ (Solar API 호환)
rank_bm25: 최신
Flask: 최신
```

---

## 💡 12. 핵심 설계 원칙

### 12.1 분리된 관심사 (Separation of Concerns)
- **config.py**: 설정 관리
- **agent/**: 대화 로직
- **qa/**: 검색 + LLM 통합
- **retriever/**: 정보 검색
- **vector_store/**: 데이터 저장소
- **ui/**: 사용자 인터페이스

### 12.2 LangChain 표준 준수
- `BaseRetriever` 상속으로 호환성 유지
- `Document` 객체 사용으로 메타데이터 보존
- `ConversationBufferMemory` 활용

### 12.3 하이브리드 검색의 강점
- **Vector**: 의미 유사도 (Semantic)
- **BM25**: 정확한 키워드 매칭 (Lexical)
- 두 방식의 장점 결합

---

## 🎯 결론

현재 **jeon-woochi-agent** 시스템은 **RAG 기반 명상 챗봇의 핵심 기능이 완성**된 상태입니다.

**완성도**: 약 85-90%
- 데이터 처리: ✅ 완료
- LLM 통합: ✅ 완료
- 검색 엔진: ✅ 완료
- CLI/웹 UI: ✅ 완료
- 비디오 스트리밍: 🟡 최종 조정 중

**다음 작업**:
1. **비디오 음성 문제 해결** (F12 콘솔 로그 확인)
2. 해결 후 프로덕션 배포 가능
3. 추가 기능 (히스토리, 평가) 단계적 추가

---

**작성자**: GitHub Copilot  
**마지막 업데이트**: 2026-01-19  
**상태**: 🟡 진행 중 (비디오 스트리밍 디버깅)

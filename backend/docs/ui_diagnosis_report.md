# UI 유지보수성 장애 — 근본 원인 진단 보고서

**작성일:** 2026-03-28  
**대상 파일:** `backend/src/ui/app.py` (Streamlit), `frontend/` (Next.js)  
**진단 범위:** 사이드바 CSS 제어 불능 → 아키텍처 전반

---

## 1. 핵심 결론 (요약)

> **사이드바를 CSS로 제어하지 못한 이유는 코드 실수가 아니라, Streamlit이 근본적으로 외부 CSS 재정의를 허용하지 않는 프레임워크이기 때문이다.**

그리고 더 중요한 사실:  

> **`frontend/` 디렉토리에 Next.js 기반 프론트엔드가 이미 완성된 상태로 존재하며, FastAPI 백엔드(`backend/src/api/main.py`)와 통신하도록 설계되어 있다. Streamlit UI를 수정할 이유가 처음부터 없었다.**

---

## 2. 프로젝트 실제 아키텍처

```
jeon-woochi-agent/
├── frontend/               ← Next.js 16 + Tailwind CSS + TypeScript
│   └── src/app/page.tsx    ← 완성된 Gemini 스타일 채팅 UI
│
└── backend/
    ├── src/api/main.py     ← FastAPI (포트 8000) — REST API + 스트리밍
    └── src/ui/app.py       ← Streamlit (포트 8502) — 병렬 실행 중인 대안 UI
```

**현재 상황:** FastAPI 백엔드가 이미 `/chat`, `/chat/stream`, `/sessions` 엔드포인트를 제공하고 있으며, Next.js 프론트엔드가 `http://localhost:8000`을 바라보도록 하드코딩되어 있다. 두 UI가 동시에 존재하는 이중 구조이나, 수정 작업은 유지보수가 불가능한 Streamlit UI에서만 이루어져 왔다.

---

## 3. Streamlit CSS 제어 불능의 기술적 원인

### 3-1. Emotion CSS-in-JS 덮어쓰기 문제

Streamlit은 내부적으로 **Emotion** (CSS-in-JS 라이브러리)을 사용하여 컴포넌트 스타일을 JavaScript 런타임에 동적으로 주입한다.

```
페이지 로드 순서:
1. HTML 초기 로드
2. st.markdown() 또는 st.html()의 <style>이 <head> 또는 <body>에 삽입
3. Streamlit JS 번들 로드
4. React + Emotion이 초기화되며 컴포넌트 트리 렌더링
5. Emotion이 <head>에 <style data-emotion="..."> 태그를 동적 삽입
   → 이 시점에서 3번의 모든 외부 CSS를 덮어씀
6. 사용자가 버튼 클릭 등으로 rerun 발생
7. 4~5번 과정이 반복됨 → 외부 CSS가 다시 덮어써짐
```

**결과:** `!important`를 아무리 붙여도, Emotion이 나중에 더 높은 specificity의 스타일을 재주입하기 때문에 영구적으로 적용되지 않는다.

### 3-2. data-testid 불안정성

Streamlit은 내부 컴포넌트의 `data-testid` 속성을 **공개 API로 보장하지 않는다.** 버전이 올라갈 때마다 이름이 변경된다.

| Streamlit 구버전 (1.x 초기) | Streamlit 1.52.x 현재 |
|---|---|
| `stVerticalBlockBorderWrapper` | `stLayoutWrapper` |
| `element-container` | `stElementContainer` |
| `column` | `stColumn` |

→ 패치 때마다 모든 CSS 셀렉터를 다시 찾아 수정해야 하는 유지보수 지옥이 발생한다.

### 3-3. iframe 격리 문제

`st.components.v1.html()`은 별도 `<iframe>` 안에서 실행된다. `window.parent.document`로 부모 DOM에 접근하는 방식은:
- 같은 origin(localhost)에서만 작동
- Streamlit의 향후 CSP(Content Security Policy) 강화 시 즉시 차단됨
- 공식 지원 방식이 아님 → 언제든 중단될 수 있음

### 3-4. min-height / flexbox 기본값

Streamlit이 사이드바에 적용하는 여백의 실제 출처:

```
stSidebarContent
  └── stVerticalBlock (flex-direction: column, gap: 1rem)  ← gap이 여백의 주원인
        ├── stElementContainer (min-height: 2.5rem)         ← 버튼 래퍼 최소 높이
        │     └── button
        └── stElementContainer
              └── button
```

`padding`을 0으로 잡아도 `gap`과 `min-height`가 여백을 만든다. 이것들도 Emotion이 매번 재주입하므로 영구 제어가 불가능하다.

---

## 4. 왜 지금까지 수정이 계속 실패했는가

```
시도 1: st.markdown() <style> → Emotion이 이후에 덮어씀
시도 2: 올바른 data-testid 수정 (stLayoutWrapper 등) → Emotion 재주입 시 무효화
시도 3: st.html() <style> → body에 삽입되지만 Emotion은 head에 삽입, specificity 우위
시도 4: components.html() + JS로 head에 주입 → Emotion의 다음 rerun에서 다시 덮어씀
시도 5: wildcard [stSidebar] * → 같은 이유로 영구 적용 불가
```

**공통 원인:** 모든 시도가 Emotion의 동적 재주입 사이클을 이기지 못했다.  
이는 버그가 아니라 Streamlit의 설계 자체다.

---

## 5. 프론트엔드 현황 — Next.js가 이미 존재한다

`frontend/src/app/page.tsx`를 분석한 결과:

| 기능 | Streamlit (app.py) | Next.js (page.tsx) |
|---|---|---|
| 사이드바 | CSS 제어 불가 | Tailwind CSS로 완전 제어 가능 ✅ |
| 새 채팅 버튼 | Streamlit 버튼 | 커스텀 HTML button + className ✅ |
| 세션 목록 | 복잡한 Python 렌더링 | map()으로 깔끔하게 렌더링 ✅ |
| 스트리밍 | 미지원 (Streamlit 특성상 어려움) | `/chat/stream` 엔드포인트 연동 ✅ |
| Markdown 렌더링 | 기본 지원 | ReactMarkdown + remarkGfm ✅ |
| 애니메이션 | 불가 | framer-motion 적용됨 ✅ |
| 다크 모드 UI | Emotion 덮어쓰기로 어려움 | Tailwind + CSS 변수로 완전 제어 ✅ |
| 유지보수성 | 매우 낮음 | 표준 React 방식 — 높음 ✅ |

Next.js 프론트엔드는 이미 `http://localhost:8000`의 FastAPI API를 호출하도록 구현되어 있다. **사이드바 스타일, 레이아웃, 각 컴포넌트 모두 일반 Tailwind CSS 클래스로 자유롭게 수정 가능하다.**

---

## 6. 권장 조치

### 즉시 — Next.js 프론트엔드로 전환

```
                   현재 (잘못된 구조)           권장 구조
                   ──────────────────           ──────────────────
사용자 브라우저 → Streamlit (8502)         사용자 브라우저 → Next.js (3000)
                   ↓ Python 내부 직접 호출               ↓ REST API 호출
                   backend/src/ui/app.py      FastAPI (8000)
                                                          ↓
                                               LangGraph Agent + VectorDB
```

### 실행 방법

```powershell
# 터미널 1: FastAPI 백엔드
cd backend
python -m uvicorn src.api.main:app --reload --port 8000

# 터미널 2: Next.js 프론트엔드
cd frontend
npm run dev
# → http://localhost:3000
```

### Next.js에서 사이드바 수정 예시

```tsx
// frontend/src/app/page.tsx
// 사이드바 여백 조정 — 그냥 Tailwind 클래스 수정하면 끝
<motion.aside 
  className="bg-[#1e1f20] h-full flex-shrink-0 border-r border-[#333]"
  // gap, padding 등 전부 className으로 제어
>
  <div className="w-[280px] p-3 flex flex-col h-full gap-1">
    {/* 완전한 제어 가능 */}
  </div>
</motion.aside>
```

---

## 7. Streamlit 유지 시 유일한 실효성 있는 방법 (비추천)

만약 어떤 이유로 Streamlit을 유지해야 한다면, **유일하게 작동하는 방법은 MutationObserver + 반복 재주입**이다.

```python
components.html("""
<script>
(function() {
    var SID = 'woochi-style';
    function inject() {
        var doc = window.parent.document;
        // Emotion이 주입한 후, 항상 마지막에 삽입되도록 MutationObserver로 감시
        var observer = new MutationObserver(function() {
            var last = doc.head.children[doc.head.children.length - 1];
            var ours = doc.getElementById(SID);
            if (!ours || ours !== last) {
                if (ours) ours.remove();
                var s = doc.createElement('style');
                s.id = SID;
                s.textContent = '/* CSS here */';
                doc.head.appendChild(s); // 항상 맨 끝
            }
        });
        observer.observe(doc.head, { childList: true, subtree: false });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inject);
    } else {
        inject();
    }
})();
</script>
""", height=0)
```

이 방법조차 Streamlit의 공식 지원 밖이며, 향후 버전 업데이트 시 즉시 깨질 수 있다. **생산 환경에서는 절대 권장하지 않는다.**

---

## 8. 결론

| 항목 | 사실 |
|---|---|
| CSS 제어 실패의 원인 | Streamlit의 Emotion CSS-in-JS가 매 rerun마다 외부 스타일을 덮어씀 — 구조적 한계 |
| data-testid 불안정 | 공개 API 아님 — 매 Streamlit 버전마다 이름 변경됨 |
| 프론트엔드 현황 | Next.js 프론트엔드가 이미 완성 상태로 `frontend/` 에 존재 |
| 백엔드 현황 | FastAPI가 이미 `/chat/stream`, `/sessions` 등 필요한 API를 모두 제공 |
| 올바른 접근 | Next.js 프론트엔드(`cd frontend && npm run dev`)를 사용 — 사이드바 포함 모든 UI를 Tailwind로 자유롭게 제어 가능 |

> **Streamlit은 데이터 분석 대시보드 도구다. 채팅 UI를 위한 프레임워크가 아니다. Next.js + FastAPI 구조가 이미 준비되어 있으며, 이쪽으로 전환하면 지금까지의 모든 CSS 문제가 즉시 사라진다.**

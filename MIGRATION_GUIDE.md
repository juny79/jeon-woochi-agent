# 전우치 명상 에이전트 - Next.js 마이그레이션 가이드

본 프로젝트는 Vercel 배포 및 최상의 UI/UX를 위해 **Next.js(Frontend) + FastAPI(Backend)** 구조로 리모델링되었습니다.

## 🏗 프로젝트 구조
- `backend/`: Python AI 엔진 및 API 서버 (ChromaDB, LangChain)
- `frontend/`: Next.js 웹 애플리케이션 (Tailwind CSS, Lucide Icons)

## 🚀 로컬 실행 방법

### 1. 백엔드 실행 (Python)
```bash
cd backend
python start.py
```
- API 서버: `http://localhost:8000`

### 2. 프론트엔드 실행 (Node.js)
```bash
cd frontend
npm run dev
```
- 웹 대화창: `http://localhost:3000`

## ☁️ Vercel 배포 안내
1. `frontend/` 폴더를 Vercel에 연결하여 배포합니다.
2. 백엔드는 별도의 클라우드(예: Render, Railway, Fly.io)에 배포하거나, Vercel Serverless Functions로 통합할 수 있습니다.
3. 환경 변수(`SOLAR_API_KEY` 등)를 Vercel Dashboard에 등록하세요.

## ✨ 변경된 디자인
- **Gemini 스타일의 다크 모드**: 세련된 그레이톤 캡슐형 입력창과 그라데이션 타이틀 적용.
- **반응형 사이드바**: 대화 내역(예정) 및 설정을 깔끔하게 관리.
- **애니메이션**: 답변 생성 시 '씽킹 빔' 로딩 효과 및 부드러운 메시지 페이드인.

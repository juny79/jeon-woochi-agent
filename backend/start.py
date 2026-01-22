import os
import sys

# 프로젝트 루트를 python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    # backend 폴더 내에서 실행되므로 src.api.main:app
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)

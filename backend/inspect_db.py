import chromadb
from src.config import Config

def inspect_chroma():
    print(f"--- [ChromaDB 점검] 경로: {Config.DB_PATH} ---")
    
    # 1. 클라이언트 연결
    client = chromadb.PersistentClient(path=Config.DB_PATH)
    
    # 2. 컬렉션 목록 조회
    collections = client.list_collections()
    
    if not collections:
        print("허허, 아직 생성된 비급(Collection)이 하나도 없구려.")
        return

    for coll in collections:
        count = coll.count()
        print(f"\n[비급명(Collection)]: {coll.name}")
        print(f" -> 지식 조각(ID) 개수: {count}개")
        
        if count > 0:
            # 상위 3개만 샘플로 가져오기
            results = coll.get(limit=3, include=["documents", "metadatas"])
            print(" -> 샘플 내용 (상위 3개):")
            for i in range(len(results["ids"])):
                content = results["documents"][i][:100] + "..." if len(results["documents"][i]) > 100 else results["documents"][i]
                metadata = results["metadatas"][i]
                print(f"    - [{results['ids'][i]}] {content}")
                print(f"      (출처: {metadata.get('source', 'unknown')})")

if __name__ == "__main__":
    inspect_chroma()

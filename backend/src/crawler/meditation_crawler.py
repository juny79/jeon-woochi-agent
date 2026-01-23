import requests
from bs4 import BeautifulSoup
import time
from src.crawler.base import BaseCrawler, TextCleaner
from langchain_core.documents import Document
from typing import List

class STBHealingCrawler(BaseCrawler):
    """동방신선학교(STB Healing) 전수 수행법 수집용 크롤러"""
    BASE_URL = "https://healing.stb.co.kr"

    def fetch_data(self, query: str = "") -> List[Document]:
        print(f"--- [STB Healing] 도술 발동: 고위 수행법을 찾고 있소 ---")
        docs = []
        # 두 개의 게시판에서 수집하여 양을 늘림
        boards = ["sunjunghwa", "news"]
        
        for board in boards:
            target_url = f"{self.BASE_URL}/board/{board}"
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(target_url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if f'/board/{board}/' in href and any(char.isdigit() for char in href):
                        links.append(href)
                
                unique_links = list(set(links))
                print(f"   [STB-{board}] {len(unique_links)}개의 비급 후보를 찾았소.")
                
                for link in unique_links[:15]: # 각 게시판당 15개씩
                    full_url = link if link.startswith('http') else f"{self.BASE_URL}{link}"
                    article_doc = self._parse_article(full_url)
                    if article_doc:
                        docs.append(article_doc)
                    time.sleep(0.3)
            except Exception as e:
                print(f"   [에러] {board} 크롤링 중 탈이 났소: {e}")
        return docs

    def _parse_article(self, url: str) -> Document:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            title = "무제"
            title_tag = soup.select_one('h4') or soup.select_one('.view-title') or soup.select_one('.title')
            if title_tag:
                title = title_tag.get_text().strip()
                
            # 본문을 찾기 위해 더 다양한 선택자 시도
            content_div = None
            for selector in ['.board-content', '.view-content', '.post-content', 'article', '.content', '#post-body']:
                content_div = soup.select_one(selector)
                if content_div and len(content_div.get_text().strip()) > 100:
                    break
            
            if not content_div:
                # 선택자로 못 찾으면 모든 P 태그 결합
                p_tags = soup.find_all('p')
                if len(p_tags) > 3:
                    content = "\n".join([p.get_text() for p in p_tags])
                else:
                    return None
            else:
                content = TextCleaner.clean(content_div.get_text())
                
            print(f"   [수집 성공] {title[:20]}...")
            return Document(
                page_content=content,
                metadata={"source": url, "title": title, "level": "advanced", "category": "stb_healing"}
            )
        except Exception:
            return None

class BasicHealthCrawler(BaseCrawler):
    """기초 명상 및 건강 관리 정보 수집용 크롤러"""
    def fetch_data(self, query: str = "기초 명상법 올바른 호흡법") -> List[Document]:
        print(f"--- [Basic Search] 도술 발동: '{query}' 기초 지식을 수집 중이오 ---")
        docs = []
        sample_contents = [
            {
                "title": "바른 자세와 복식호흡의 기초",
                "content": "명상의 시작은 척추를 바로 세우고 어깨의 힘을 빼는 것이다. 코로 깊게 들이마셔 아랫배(단전)를 부풀리고, 입으로 가늘고 길게 내뱉는 복식호흡은 심신의 안정을 가져다주는 가장 기초적인 도술이다. 하루 10분만 투자해도 뇌파가 안정되고 스트레스 호르몬인 코르티솔 수치가 낮아진다는 연구 결과가 있소.",
                "url": "https://health.sample.com/basic-breathing"
            },
            {
                "title": "잡념을 다스리는 마음챙김 기초",
                "content": "초보자는 잡념에 휘둘리기 쉽다. 생각이 떠오를 때는 이를 억누르려 하지 말고, 강물에 떠내려가는 나뭇잎을 보듯 무심히 관찰하라. 그리고 다시 자신의 호흡으로 주의를 돌리는 것이 기초 연마의 핵심이다. 이것이 바로 서양에서 유행하는 마인드풀니스(Mindfulness)의 요체이기도 하오.",
                "url": "https://mind.sample.com/intro-meditation"
            },
            {
                "title": "잠들기 전 수면 명상 비법",
                "content": "잠이 오지 않을 때는 몸의 각 부위에 집중하며 긴장을 푸는 '바디 스캔' 명상이 효과적이오. 발가락부터 머리끝까지 천천히 의식을 이동하며 무거워지는 느낌을 느껴보시오. 숙면은 만병통치의 근본이라 하였소.",
                "url": "https://health.sample.com/sleep-meditation"
            },
            {
                "title": "걷기 명상: 행선(行禪)의 도술",
                "content": "명상은 앉아서만 하는 것이 아니오. 걸으면서도 충분히 할 수 있지. 발바닥이 땅에 닿는 감각, 다리의 움직임, 숨의 리듬에 집중하며 천천히 걷는 행선은 일상 속에서도 도를 닦는 좋은 방법이오.",
                "url": "https://health.sample.com/walking-meditation"
            },
            {
                "title": "스트레스 해소와 심장 호흡",
                "content": "가슴에 손을 얹고 심장의 고동을 느끼며 호흡해보시오. 사랑하는 사람이나 감사한 기억을 떠올리며 호흡하면 심박 변이도(HRV)가 개선되어 급작스러운 분노나 불안을 잠재울 수 있소.",
                "url": "https://health.sample.com/heart-coherence"
            }
        ]
        for item in sample_contents:
            docs.append(Document(
                page_content=item["content"],
                metadata={"source": item["url"], "title": item["title"], "level": "basic", "category": "health_management"}
            ))
        return docs

class MeditationNewsCrawler(BaseCrawler):
    def fetch_data(self, query: str = "기초 명상") -> List[Document]:
        basic = BasicHealthCrawler().fetch_data(query)
        advanced = STBHealingCrawler().fetch_data()
        return basic + advanced

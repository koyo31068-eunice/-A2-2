import requests
from bs4 import BeautifulSoup
import sqlite3
import logging
from database import get_connection

logger = logging.getLogger(__name__)

def fetch_from_api(api_key, limit=5):
    """실제 NewsAPI(newsapi.org)를 통해 뉴스 수집"""
    logger.info("NewsAPI를 통해 실제 뉴스 수집을 시도합니다...")
    
    if not api_key or api_key == "YOUR_NEWS_API_KEY":
        logger.error("NewsAPI 키가 설정되지 않았습니다. config.json을 확인해 주세요.")
        return []
        
    # 국가: us(미국), 카테고리: technology(IT/기술)
    url = f"https://newsapi.org/v2/top-headlines?country=us&category=technology&pageSize={limit}&apiKey={api_key}"
    
    news_list = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("articles", [])
        
        for article in articles:
            # NewsAPI는 본문(content)이 잘려서 오는 경우가 많아, 상세 설명(description)을 함께 활용합니다.
            raw_content = article.get("description") or article.get("content") or ""
            
            news_list.append({
                "title": article.get("title", "제목 없음"),
                "content": raw_content,
                "source": article.get("source", {}).get("name", "NewsAPI"),
                "url": article.get("url", "")
            })
            
        logger.info(f"NewsAPI에서 {len(news_list)}개의 기사를 성공적으로 가져왔습니다.")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API 요청 중 오류가 발생했습니다: {e}")
        
    return news_list

def fetch_from_scraping(limit=5):
    """방법 2: BeautifulSoup을 활용한 웹 크롤링"""
    logger.info("웹 크롤링으로 뉴스 수집을 시도합니다...")
    url = "https://news.ycombinator.com/"
    
    news_list = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        story_tags = soup.find_all('span', class_='titleline')[:limit]
        
        for tag in story_tags:
            link_tag = tag.find('a')
            if link_tag:
                news_list.append({
                    "title": link_tag.text,
                    "content": "크롤링 데이터 (본문 직접 접근 필요)",
                    "source": "HackerNews",
                    "url": link_tag['href']
                })
        logger.info(f"크롤링으로 {len(news_list)}개의 기사를 가져왔습니다.")
        
    except Exception as e:
        logger.error(f"크롤링 중 오류가 발생했습니다: {e}")
        
    return news_list

def save_raw_news(news_list, db_path):
    """수집한 뉴스를 raw_news 테이블에 저장"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    saved_count = 0
    
    for news in news_list:
        try:
            cursor.execute('''
                INSERT INTO raw_news (title, content, source, url)
                VALUES (?, ?, ?, ?)
            ''', (news['title'], news['content'], news['source'], news['url']))
            saved_count += 1
        except sqlite3.IntegrityError:
            pass 
            
    conn.commit()
    conn.close()
    logger.info(f"DB에 총 {saved_count}개의 새로운 뉴스가 저장되었습니다. (중복 제외)")
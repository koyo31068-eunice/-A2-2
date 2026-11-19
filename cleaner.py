import re
import sqlite3
import logging
from datetime import datetime
from database import get_connection

logger = logging.getLogger(__name__)

def clean_text(text):
    """HTML 태그 제거 및 연속된 공백을 하나로 압축"""
    if not text:
        return ""
    # 간단한 HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    # 줄바꿈(\n)이나 연속된 띄어쓰기를 단일 공백으로 치환
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_date(date_str):
    """문자열에서 YYYY-MM-DD 형식의 날짜만 추출"""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    
    match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
    if match:
        return match.group(0)
    
    return datetime.now().strftime("%Y-%m-%d")

def run_cleaning(db_path, duplicate_policy="skip"):
    logger.info(f"데이터 정제를 시작합니다. (중복 정책: {duplicate_policy})")
    conn = get_connection(db_path)
    # 데이터를 딕셔너리처럼 이름으로 접근할 수 있게 해주는 옵션입니다.
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    # 원본 테이블에서 데이터 가져오기
    cursor.execute("SELECT * FROM raw_news")
    raw_rows = cursor.fetchall()
    
    saved_count = 0
    skipped_count = 0
    
    for row in raw_rows:
        # 데이터 정제 수행
        title = clean_text(row['title'])
        content = clean_text(row['content'])
        source = clean_text(row['source'])
        url = row['url']
        # 수집 시간을 발행일 기준으로 사용 (필요시 기사 본문의 날짜 활용 가능)
        published_date = extract_date(row['fetch_time']) 
        
        # 필수 검증: 제목이나 주소가 비어있으면 불량 데이터로 간주하고 버림
        if not title or not url:
            continue
            
        try:
            if duplicate_policy == "skip":
                # URL이 중복되면 에러(IntegrityError)를 발생시키고 except로 빠짐
                cursor.execute('''
                    INSERT INTO clean_news (title, content, source, url, published_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, content, source, url, published_date))
                saved_count += 1
                
            elif duplicate_policy == "upsert":
                # URL이 중복되면 기존 데이터를 최신 정제 데이터로 덮어씀
                cursor.execute('''
                    INSERT INTO clean_news (title, content, source, url, published_date)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        title=excluded.title,
                        content=excluded.content,
                        source=excluded.source,
                        published_date=excluded.published_date
                ''', (title, content, source, url, published_date))
                saved_count += 1
                
        except sqlite3.IntegrityError:
            skipped_count += 1

    conn.commit()
    conn.close()
    
    logger.info(f"데이터 정제 완료: {saved_count}개 저장됨, {skipped_count}개 스킵됨.")
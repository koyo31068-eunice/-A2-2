import sqlite3
import logging

logger = logging.getLogger(__name__)

def get_connection(db_path="news.db"):
    return sqlite3.connect(db_path)

def init_db(db_path="news.db"):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # 1. 원본 뉴스를 저장할 테이블 (raw_news)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            source TEXT,
            url TEXT UNIQUE,
            fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. 정제된 뉴스와 요약본을 저장할 테이블 (clean_news)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clean_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            source TEXT,
            url TEXT UNIQUE,
            published_date TEXT,
            summary TEXT,
            is_summarized INTEGER DEFAULT 0
        )
    ''')
    
    # 3. AI 인사이트 분석 결과를 저장할 테이블 (insights)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_type TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("데이터베이스 테이블 초기화가 완료되었습니다.")
import sqlite3
import logging
import time
from google import genai
from database import get_connection

logger = logging.getLogger(__name__)

def summarize_text(text, api_key):
    """최신 구글 Gemini API(google-genai)를 활용하여 텍스트를 요약합니다."""
    # API 키가 입력되지 않은 경우 테스트용 가짜 데이터 반환
    if not api_key or api_key == "YOUR_AI_API_KEY":
        time.sleep(0.3)
        return "[테스트 요약] AI API 키가 없어 생성된 임시 요약문입니다. 본문 일부: " + text[:30] + "..."
        
    try:
        # 새로운 genai SDK 클라이언트 초기화
        client = genai.Client(api_key=api_key)
        
        prompt = f"다음 뉴스 기사의 핵심 내용을 3줄 이내로 간결하게 요약해 줘:\n\n{text}"
        
        # gemini-2.5-flash 모델 호출
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"API 통신 오류: {e}")
        return "요약 실패"

def run_summarization(db_path, api_key, target="unsummarized"):
    logger.info(f"뉴스 요약을 시작합니다. (대상: {target})")
    conn = get_connection(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 옵션에 따라 요약할 대상 기사 불러오기
    if target == "all":
        cursor.execute("SELECT id, title, content FROM clean_news")
    else:
        cursor.execute("SELECT id, title, content FROM clean_news WHERE is_summarized = 0")
        
    rows = cursor.fetchall()
    if not rows:
        logger.info("요약할 기사가 없습니다.")
        return
        
    logger.info(f"총 {len(rows)}개의 기사를 요약합니다.")
    
    success_count = 0
    for row in rows:
        article_id = row['id']
        content = row['content']
        
        if len(content) < 20:
            logger.warning(f"[{article_id}] 본문이 너무 짧아 요약을 건너뜁니다.")
            continue
            
        summary = summarize_text(content, api_key)
        
        if summary != "요약 실패":
            cursor.execute('''
                UPDATE clean_news 
                SET summary = ?, is_summarized = 1
                WHERE id = ?
            ''', (summary, article_id))
            success_count += 1
            logger.info(f"[{article_id}] 기사 요약 완료")

        # --------- 이 부분(2줄)을 추가해 주세요! ---------
        logger.info("API 속도 제한(Rate Limit) 방지를 위해 20초 대기합니다...")
        time.sleep(20)
        # -----------------------------------------------
            
    conn.commit()
    conn.close()
    logger.info(f"뉴스 요약 작업이 종료되었습니다. (성공: {success_count}개)")

def run_analysis(db_path, api_key, category=None):
    logger.info("AI 인사이트 분석을 시작합니다.")
    
    if not api_key or api_key == "YOUR_AI_API_KEY":
        logger.error("유효한 API 키가 설정되지 않아 분석을 진행할 수 없습니다.")
        return

    conn = get_connection(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT title, summary FROM clean_news WHERE is_summarized = 1")
    rows = cursor.fetchall()
    
    if not rows:
        logger.warning("분석할 요약 기사가 없습니다. 먼저 요약을 진행해 주세요.")
        conn.close()
        return
        
    logger.info(f"총 {len(rows)}개의 기사를 바탕으로 종합 분석을 요청합니다...")
    
    combined_text = ""
    for row in rows:
        combined_text += f"- 제목: {row['title']}\n  요약: {row['summary']}\n\n"
        
    prompt = f"""
    다음은 최근 수집된 뉴스 기사들의 요약본 모음입니다.
    이 데이터들을 종합적으로 분석하여 아래 3가지 항목이 포함된 인사이트 리포트를 작성해 주세요.
    각 항목은 보기 좋게 마크다운 문법으로 정리해 주세요.
    
    1. 주요 트렌드: 기사들을 관통하는 공통된 핵심 주제나 흐름
    2. 핵심 키워드: 분석 내용을 대표하는 주요 단어 5개 (콤마로 구분)
    3. 시사점: 이 뉴스들이 시사하는 바와 향후 전망
    
    [뉴스 데이터 모음]
    {combined_text}
    """
    
    # --- 여기서부터 재시도(Retry) 로직이 추가되었습니다 ---
    max_retries = 3  # 최대 3번까지 재시도
    
    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            insight_result = response.text.strip()
            
            analysis_type = category if category else "종합 트렌드 분석"
            cursor.execute('''
                INSERT INTO insights (analysis_type, content)
                VALUES (?, ?)
            ''', (analysis_type, insight_result))
            
            conn.commit()
            logger.info("AI 분석이 완료되어 데이터베이스에 성공적으로 저장되었습니다!")
            break  # 성공하면 반복문을 탈출합니다!
            
        except Exception as e:
            # 에러 메시지에 503(서버 혼잡)이나 429(속도 제한)가 포함된 경우
            if "503" in str(e) or "429" in str(e):
                if attempt < max_retries - 1:
                    logger.warning(f"서버 혼잡 발생! 10초 대기 후 재시도합니다... (시도 횟수: {attempt + 1}/{max_retries})")
                    time.sleep(10)
                else:
                    logger.error(f"서버가 계속 혼잡하여 분석에 실패했습니다: {e}")
            else:
                # 다른 종류의 심각한 에러면 재시도하지 않고 바로 종료
                logger.error(f"분석 중 통신 오류가 발생했습니다: {e}")
                break 
    # --------------------------------------------------
    
    conn.close()
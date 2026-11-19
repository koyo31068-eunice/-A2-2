import sqlite3
import logging
import pandas as pd
import matplotlib.pyplot as plt
import os
from database import get_connection

logger = logging.getLogger(__name__)

# 한글 폰트 설정 (Windows/Mac 공통으로 시도)
try:
    if os.name == 'nt':  # Windows
        plt.rc('font', family='Malgun Gothic')
    else:  # Mac
        plt.rc('font', family='AppleGothic')
    plt.rcParams['axes.unicode_minus'] = False # 마이너스 기호 깨짐 방지
except Exception as e:
    logger.warning(f"폰트 설정 실패 (기본 폰트 사용): {e}")

def run_report(db_path):
    logger.info("리포트 및 시각화를 생성합니다.")
    conn = get_connection(db_path)
    
    # 1. Pandas를 이용해 DB 데이터를 DataFrame으로 바로 읽어오기
    df_raw = pd.read_sql_query("SELECT * FROM raw_news", conn)
    df_clean = pd.read_sql_query("SELECT * FROM clean_news", conn)
    
    if df_clean.empty:
        logger.warning("리포트를 생성할 데이터가 없습니다.")
        conn.close()
        return

    # 2. 품질 지표 계산 및 출력
    total_raw = len(df_raw)
    total_clean = len(df_clean)
    summarized_count = len(df_clean[df_clean['is_summarized'] == 1])
    
    print("\n" + "="*40)
    print(" 📊 데이터 파이프라인 품질 리포트")
    print("="*40)
    print(f" - 수집된 원본 데이터: {total_raw}건")
    print(f" - 정제 완료된 데이터: {total_clean}건")
    print(f" - AI 요약 완료: {summarized_count}건 ({summarized_count/total_clean*100:.1f}%)")
    print("="*40 + "\n")

    # 3. 데이터 시각화 (출처별 뉴스 분포 파이 차트)
    source_counts = df_clean['source'].value_counts()
    
    plt.figure(figsize=(8, 6))
    source_counts.plot(kind='pie', autopct='%1.1f%%', startangle=90, cmap='Pastel1')
    plt.title('수집된 뉴스 출처(Source) 분포')
    plt.ylabel('') # y축 라벨 숨기기
    
    # 차트를 이미지 파일로 저장
    plt.savefig('news_source_chart.png')
    logger.info("시각화 차트가 'news_source_chart.png'로 저장되었습니다.")
    
    conn.close()

def export_data(db_path, format_type="csv"):
    logger.info(f"데이터를 {format_type} 형식으로 내보냅니다.")
    conn = get_connection(db_path)
    
    # 내보낼 데이터 가져오기
    df = pd.read_sql_query("SELECT * FROM clean_news", conn)
    conn.close()
    
    if df.empty:
        logger.warning("내보낼 데이터가 없습니다.")
        return

    try:
        if format_type == "csv":
            df.to_csv("news_export.csv", index=False, encoding='utf-8-sig')
            logger.info("news_export.csv 파일 생성이 완료되었습니다.")
        elif format_type == "excel":
            df.to_excel("news_export.xlsx", index=False, engine='openpyxl')
            logger.info("news_export.xlsx 파일 생성이 완료되었습니다.")
    except Exception as e:
        logger.error(f"파일 내보내기 실패: {e}")
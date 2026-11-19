import argparse
from config import setup_logger, load_config
from database import init_db
from fetcher import fetch_from_api, fetch_from_scraping, save_raw_news
from cleaner import run_cleaning
from ai_handler import run_summarization, run_analysis
from reporter import run_report, export_data

# 로거 세팅
logger = setup_logger()

def main():
    # 1. argparse 뼈대 만들기
    parser = argparse.ArgumentParser(description="AI 기반 뉴스 수집 및 분석 파이프라인")
    subparsers = parser.add_subparsers(dest="command", help="실행할 작업을 선택하세요.")

    # 각 서브커맨드(명령어) 등록 및 옵션 추가
    parser_fetch = subparsers.add_parser("fetch", help="뉴스 데이터 수집")
    parser_fetch.add_argument("--limit", type=int, default=10, help="수집할 기사 수")

    parser_clean = subparsers.add_parser("clean", help="수집된 데이터 정제")

    parser_summarize = subparsers.add_parser("summarize", help="뉴스 요약")
    parser_summarize.add_argument("--target", choices=["all", "unsummarized"], default="unsummarized", help="요약 대상")

    parser_analyze = subparsers.add_parser("analyze", help="인사이트 도출")
    parser_analyze.add_argument("--category", type=str, help="분석할 카테고리 지정")

    parser_report = subparsers.add_parser("report", help="리포트 생성 및 시각화")

    parser_export = subparsers.add_parser("export", help="데이터 내보내기")
    parser_export.add_argument("--format", choices=["csv", "excel"], default="csv", help="내보낼 포맷")

    # 2. 사용자 입력 분석
    args = parser.parse_args()
    config = load_config()

    # 3. 명령어에 따른 분기 처리
    if args.command == "fetch":
        logger.info(f"뉴스 수집을 시작합니다. (요청 수량: {args.limit}개)")
        
        # 1. API로 뉴스 가져오기
        api_key = config.get("api_keys", {}).get("news_api", "")
        api_news = fetch_from_api(api_key, limit=args.limit)
        
        # 2. 크롤링으로 뉴스 가져오기
        scraped_news = fetch_from_scraping(limit=args.limit)
        
        # 3. 두 결과물을 하나로 합쳐서 DB에 저장하기
        all_news = api_news + scraped_news
        save_raw_news(all_news, config.get("db_path", "news.db"))
    elif args.command == "clean":
        # config.json에서 중복 정책을 읽어옵니다 (기본값은 skip)
        duplicate_policy = config.get("duplicate_policy", "skip")
        db_path = config.get("db_path", "news.db")
        
        run_cleaning(db_path, duplicate_policy)
    elif args.command == "summarize":
        db_path = config.get("db_path", "news.db")
        # config.json에서 AI API 키를 읽어옵니다
        ai_api_key = config.get("api_keys", {}).get("ai_api", "")
        
        # 이 줄이 있어야 실제로 AI 요약 작업이 실행됩니다!
        run_summarization(db_path, ai_api_key, target=args.target)
    elif args.command == "analyze":
        db_path = config.get("db_path", "news.db")
        ai_api_key = config.get("api_keys", {}).get("ai_api", "")
        
        run_analysis(db_path, ai_api_key, category=args.category)
    elif args.command == "report":
        db_path = config.get("db_path", "news.db")
        run_report(db_path)       
    elif args.command == "export":
        db_path = config.get("db_path", "news.db")
        export_data(db_path, format_type=args.format)
    else:
        # 명령어를 입력하지 않고 실행했을 때
        init_db(config.get("db_path", "news.db"))
        parser.print_help()

if __name__ == "__main__":
    main()
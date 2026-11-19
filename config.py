import json
import logging

def load_config():
    # config.json 파일을 읽어서 파이썬 딕셔너리로 반환합니다.
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def setup_logger():
    # 로그(기록)의 형태와 수준을 설정합니다.
    config = load_config()
    logging.basicConfig(
        level=getattr(logging, config.get("log_level", "INFO")),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)
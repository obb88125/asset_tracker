"""
자산 추적기 설정 파일
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 데이터베이스 설정
DATABASE_PATH = os.path.join(BASE_DIR, "instance", "asset_tracker.db")
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"

# 업로드 설정
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

# Flask 설정
SECRET_KEY = os.environ.get("SECRET_KEY", "asset-tracker-dev-secret-key-2024")
DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

# 허용 파일 확장자
ALLOWED_EXTENSIONS = {"xlsx", "xls", "csv"}


def allowed_file(filename: str) -> bool:
    """업로드 파일 확장자 검증"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

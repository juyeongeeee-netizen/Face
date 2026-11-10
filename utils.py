"""환경변수 로딩, 이미지 검증·전처리 유틸리티."""

import base64
import hashlib
import io
import os
import warnings

import streamlit as st
from dotenv import load_dotenv
from PIL import Image, ImageOps, UnidentifiedImageError

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
MAX_SIDE = 1024
MAX_FILE_MB = 10
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
# 압축률이 높은 이미지는 파일은 작아도 해상도가 거대할 수 있다 (압축 폭탄).
# 5천만 픽셀이면 최신 스마트폰 고화소 사진(약 8000x6000)까지 허용된다.
MAX_PIXELS = 50_000_000

INVALID_IMAGE_MESSAGE = "올바른 이미지 파일이 아닙니다. JPG, PNG, WEBP 사진을 올려주세요."
TOO_MANY_PIXELS_MESSAGE = "이미지 해상도가 너무 커요. 5천만 화소(예: 8000×6000) 이하 사진을 올려주세요."


def get_secret(key: str, default: str | None = None) -> str | None:
    """st.secrets(Streamlit Cloud)를 먼저 찾고, 없으면 .env/환경변수에서 값을 읽는다."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # 로컬에 secrets.toml이 없으면 st.secrets 접근 시 예외가 난다.
        pass
    return os.getenv(key, default)


def is_too_large(data: bytes) -> bool:
    """파일 크기가 업로드 제한(10MB)을 넘는지 확인한다."""
    return len(data) > MAX_FILE_BYTES


def validate_image(data: bytes) -> str | None:
    """이미지를 끝까지 디코딩해 본다. 문제가 있으면 안내 문구, 정상이면 None을 반환한다.

    - 해상도 검사는 디코딩 전에 한다 (헤더만 읽으므로 압축 폭탄도 메모리를 쓰지 않는다).
    - verify()는 잘린 JPEG를 통과시키므로 load()로 실제 픽셀까지 읽어 확인한다.
    """
    try:
        with warnings.catch_warnings():
            # Pillow의 DecompressionBombWarning도 오류로 취급한다.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                width, height = image.size
                if width * height > MAX_PIXELS:
                    return TOO_MANY_PIXELS_MESSAGE
                image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        return TOO_MANY_PIXELS_MESSAGE
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError):
        return INVALID_IMAGE_MESSAGE
    return None


def preprocess_image(data: bytes) -> str:
    """이미지 바이트를 EXIF 회전 보정·리사이즈·JPEG 변환 후 base64 문자열로 반환한다 (메모리에서만 처리)."""
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image)
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    if image.mode != "RGB":
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def image_hash(data: bytes) -> str:
    """세션 캐시 키로 쓸 이미지 바이트의 SHA-256 해시를 반환한다."""
    return hashlib.sha256(data).hexdigest()

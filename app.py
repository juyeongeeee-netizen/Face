"""AI 관상가 - Streamlit 메인 앱 (화면 흐름만 담당)."""

import random
from datetime import datetime

import streamlit as st

from ai import AnalysisError, NoFaceError, analyze_face
from prompts import DEFAULT_STYLE, STYLE_CAPTIONS, STYLE_PROMPTS
from styles import (
    HERO_HTML,
    LOADING_MESSAGES,
    RESULT_KEY,
    format_result,
    inject_styles,
    paper_header_html,
)
from utils import (
    DEFAULT_MODEL,
    MAX_FILE_MB,
    get_secret,
    image_hash,
    is_too_large,
    preprocess_image,
    validate_image,
)

DISCLAIMER = "재미로 보는 결과이며 과학적 근거가 없습니다."
PRIVACY_NOTICE = "업로드한 이미지는 저장되지 않으며, 분석에만 사용됩니다."

st.set_page_config(page_title="AI 관상가", page_icon="🔮", layout="centered")
inject_styles()

# ---------- 세션 상태 ----------
st.session_state.setdefault("results", {})        # {캐시키: {"text", "filename"}}
st.session_state.setdefault("active_source", None)  # 마지막으로 입력된 소스: "upload" | "camera"
st.session_state.setdefault("force_reanalyze", False)


def set_active_source(source: str) -> None:
    """업로드/카메라 중 마지막으로 바뀐 입력을 기억한다."""
    st.session_state.active_source = source


def request_reanalyze() -> None:
    """'다시 분석하기' 버튼 클릭 시 다음 실행에서 캐시를 무시하도록 표시한다."""
    st.session_state.force_reanalyze = True


def show_footer() -> None:
    """면책·개인정보 안내를 화면 하단에 항상 표시한다."""
    st.divider()
    st.caption(f"⚠️ {DISCLAIMER}  \n🔒 {PRIVACY_NOTICE}")


# ---------- 사이드바 ----------
with st.sidebar:
    st.header("⚙️ 설정")
    style_names = list(STYLE_PROMPTS)
    style = st.radio(
        "풀이 스타일",
        style_names,
        index=style_names.index(DEFAULT_STYLE),
        captions=[STYLE_CAPTIONS[name] for name in style_names],
    )
    st.divider()
    st.info(f"🔒 {PRIVACY_NOTICE}")
    st.warning(f"⚠️ {DISCLAIMER}")

# ---------- 헤더 ----------
st.markdown(HERO_HTML, unsafe_allow_html=True)

api_key = get_secret("OPENAI_API_KEY")
model = get_secret("OPENAI_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL

if not api_key:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일 또는 Streamlit Secrets를 확인해 주세요.")
    show_footer()
    st.stop()

# ---------- 입력 (업로드 / 카메라) ----------
tab_upload, tab_camera = st.tabs(["📁 사진 업로드", "📷 카메라 촬영"])
with tab_upload:
    uploaded = st.file_uploader(
        f"얼굴이 잘 보이는 정면 사진을 올려주세요 (최대 {MAX_FILE_MB}MB)",
        type=["jpg", "jpeg", "png", "webp"],
        max_upload_size=MAX_FILE_MB,  # 업로드 영역 안내 문구도 실제 제한(10MB)과 일치시킨다
        key="upload",
        on_change=set_active_source,
        args=("upload",),
    )
with tab_camera:
    captured = st.camera_input(
        "정면을 바라보고 촬영해 주세요",
        key="camera",
        on_change=set_active_source,
        args=("camera",),
    )

# 마지막으로 들어온 입력을 우선 사용하고, 그 입력이 지워졌으면 남아 있는 쪽을 사용
sources = {"upload": uploaded, "camera": captured}
image_file = sources.get(st.session_state.active_source) or uploaded or captured

if image_file is None:
    st.info("👆 사진을 올리거나 카메라로 촬영해 주세요.")
    show_footer()
    st.stop()

# ---------- 검증 + 미리보기 ----------
image_bytes = image_file.getvalue()
error_message = None
if is_too_large(image_bytes):
    error_message = f"파일이 너무 커요 ({len(image_bytes) / 1024 / 1024:.1f}MB). {MAX_FILE_MB}MB 이하 사진을 올려주세요."
    st.warning(error_message)
else:
    error_message = validate_image(image_bytes)
    if error_message:
        st.error(error_message)
    else:
        _, col_preview, _ = st.columns([1, 2, 1])
        with col_preview:
            st.image(image_bytes, caption="분석할 사진", use_container_width=True)

can_analyze = error_message is None
cache_key = f"{image_hash(image_bytes)}:{style}"
results = st.session_state.results

analyze_clicked = st.button(
    "🔮 관상 보기", type="primary", disabled=not can_analyze, use_container_width=True
)
force = st.session_state.force_reanalyze
st.session_state.force_reanalyze = False

# ---------- 분석 ----------
analysis_failed = False  # 이번 실행에서 분석이 실패하면 이전 결과를 함께 보여주지 않는다
if can_analyze and (analyze_clicked or force):
    if cache_key in results and not force:
        st.toast("이전에 본 관상 결과를 불러왔어요.")
    else:
        try:
            with st.spinner(random.choice(LOADING_MESSAGES)):
                try:
                    image_b64 = preprocess_image(image_bytes)
                except Exception:
                    # 검증을 통과했더라도 변환 중 실패할 수 있으므로 앱이 멈추지 않게 안내로 바꾼다.
                    raise AnalysisError("사진을 처리하지 못했어요. 다른 사진으로 다시 시도해 주세요.")
                text = analyze_face(image_b64, api_key, model, style)
            results[cache_key] = {
                "text": text,
                "filename": f"gwansang_{datetime.now():%Y%m%d_%H%M%S}.md",
            }
            st.toast("관상 풀이가 나왔어요.", icon="📜")
        except NoFaceError as e:
            results.pop(cache_key, None)
            analysis_failed = True
            st.warning(e.message)
        except AnalysisError as e:
            analysis_failed = True
            st.error(e.message)

# ---------- 결과 ----------
result = results.get(cache_key) if can_analyze and not analysis_failed else None
if result:
    with st.container(border=True, key=RESULT_KEY):
        st.markdown(paper_header_html(style), unsafe_allow_html=True)
        st.markdown(format_result(result["text"]), unsafe_allow_html=True)

    col_download, col_retry = st.columns(2)
    with col_download:
        st.download_button(
            "📥 결과 다운로드",
            data=result["text"],
            file_name=result["filename"],
            mime="text/markdown",
            on_click="ignore",
            use_container_width=True,
        )
    with col_retry:
        st.button("🔄 다시 분석하기", on_click=request_reanalyze, use_container_width=True)

show_footer()

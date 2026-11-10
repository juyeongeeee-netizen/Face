"""화면 스타일(CSS)과 HTML 조각.

Streamlit 내부 클래스명 대신 key로 생기는 `.st-key-*` 클래스와 `data-testid`만 사용한다.
CSS가 적용되지 않아도 기능은 그대로 동작한다.
"""

import html
import re

import streamlit as st

RESULT_KEY = "result_paper"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Nanum+Brush+Script&display=swap');

:root {
  --ink: #141A2E;
  --night: #1E2640;
  --gold: #C9A45C;
  --gold-deep: #8A6A2B;
  --hanji: #EFE6D2;
  --meok: #2A2420;
  --seal: #A8322D;
  --mist: #E9E2D0;
  --rod: #5B4326;
}

/* 본문 서체: 아이콘(Material) span은 건드리지 않도록 텍스트 요소만 지정 */
.stApp :is(p, li, label, h1, h2, h3, h4, input, textarea, button) {
  font-family: 'Gowun Dodum', sans-serif;
}

/* ---------- 히어로 ---------- */
.hero { text-align: center; padding: 1.5rem 0 0.5rem; }
.hero h1 {
  font-family: 'Nanum Brush Script', cursive !important;
  font-weight: 400;
  font-size: clamp(3rem, 12vw, 4.75rem);
  line-height: 1;
  color: var(--gold);
  margin: 0;
  padding: 0;
  letter-spacing: 0.02em;
}
.hero .sub {
  color: var(--mist);
  opacity: 0.8;
  margin: 0.6rem 0 1.5rem;
  font-size: 1.05rem;
}
.steps {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem 1.75rem;
  padding: 0;
  margin: 0 0 1.25rem;
  counter-reset: step;
}
.steps li {
  counter-increment: step;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  color: var(--mist);
  font-size: 0.95rem;
}
.steps li::before {
  content: counter(step);
  display: inline-grid;
  place-items: center;
  width: 1.6rem;
  height: 1.6rem;
  border: 1px solid var(--gold);
  border-radius: 50%;
  color: var(--gold);
  font-size: 0.85rem;
}

/* ---------- 주요 버튼: 금박 위 먹색 글씨 ---------- */
[data-testid="stBaseButton-primary"] {
  min-height: 3.25rem;
}
[data-testid="stBaseButton-primary"] p {
  color: var(--ink);
  font-size: 1.1rem;
  font-weight: 700;
}

/* ---------- 결과: 한지 두루마리 ---------- */
.st-key-result_paper {
  position: relative;
  background:
    radial-gradient(ellipse at 20% 10%, rgba(255, 255, 255, 0.35), transparent 55%),
    radial-gradient(ellipse at 85% 90%, rgba(140, 110, 60, 0.12), transparent 60%),
    var(--hanji) !important;
  border: none !important;
  border-top: 12px solid var(--rod) !important;
  border-bottom: 12px solid var(--rod) !important;
  border-radius: 6px !important;
  padding: 2rem 1.75rem 1.5rem !important;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
  animation: unroll 0.7s ease-out;
  transform-origin: top center;
}
.st-key-result_paper :is(p, li, strong, em, span, h2, h3) {
  color: var(--meok);
}
.st-key-result_paper h2 {
  font-family: 'Nanum Brush Script', cursive !important;
  font-weight: 400;
  font-size: 2rem;
  margin: 1.4rem 0 0.4rem;
  padding: 0 0 0.25rem;
  border-bottom: 1px solid rgba(42, 36, 32, 0.18);
}
.st-key-result_paper h2:first-of-type { margin-top: 0.25rem; }
.st-key-result_paper li { line-height: 1.75; }
.st-key-result_paper :is(h2, h3) a { display: none; }  /* 제목 앵커 아이콘 숨김 */

/* 낙관이 본문을 가리지 않도록 머리줄이 인장 높이만큼 자리를 차지한다 */
.paper-meta {
  min-height: 4.25rem;
  display: flex;
  align-items: flex-start;
  font-size: 0.9rem;
  opacity: 0.7;
  margin: 0 5rem 0 0 !important;
}
.seal {
  position: absolute;
  top: 1.25rem;
  right: 1.25rem;
  width: 4rem;
  height: 4rem;
  display: grid;
  place-items: center;
  border: 3px solid var(--seal);
  border-radius: 6px;
  color: var(--seal);
  font-family: serif;
  font-size: 1.45rem;
  font-weight: 700;
  line-height: 1.05;
  writing-mode: vertical-rl;
  transform: rotate(-6deg);
  opacity: 0.88;
  pointer-events: none;
}
.stars .on { color: var(--gold-deep); letter-spacing: 0.08em; }
.stars .off { color: rgba(42, 36, 32, 0.25); letter-spacing: 0.08em; }

@keyframes unroll {
  from { opacity: 0; transform: scaleY(0.92); }
  to   { opacity: 1; transform: scaleY(1); }
}
@media (prefers-reduced-motion: reduce) {
  .st-key-result_paper { animation: none; }
}

@media (max-width: 480px) {
  .st-key-result_paper { padding: 1.5rem 1.1rem 1.25rem !important; }
  .seal { width: 3.2rem; height: 3.2rem; font-size: 1.15rem; top: 1rem; right: 0.9rem; }
  .paper-meta { margin-right: 3.75rem !important; min-height: 3.5rem; }
}
</style>
"""

HERO_HTML = """
<div class="hero">
  <h1>🔮 AI 관상가</h1>
  <p class="sub">얼굴 사진 한 장으로 재미 삼아 보는 나의 관상</p>
  <ol class="steps">
    <li>사진 올리기</li>
    <li>관상 보기 누르기</li>
    <li>두루마리 풀이 읽기</li>
  </ol>
</div>
"""

LOADING_MESSAGES = [
    "관상가가 이마를 살피는 중...",
    "눈빛을 읽는 중...",
    "콧대에 깃든 재물운을 가늠하는 중...",
    "입꼬리에 담긴 말복을 헤아리는 중...",
    "턱선에서 말년운을 짚어보는 중...",
    "먹을 갈고 붓을 드는 중...",
]

_STAR_RUN = re.compile(r"[★☆]{2,}")


def inject_styles() -> None:
    """전역 CSS를 페이지에 주입한다."""
    st.markdown(CSS, unsafe_allow_html=True)


def paper_header_html(style: str) -> str:
    """두루마리 상단의 스타일 표기와 낙관(인장) HTML을 반환한다."""
    return (
        '<div class="seal" aria-hidden="true">觀相</div>'
        f'<p class="paper-meta">{html.escape(style)}의 풀이</p>'
    )


def _stars_html(match: re.Match) -> str:
    run = match.group(0)
    filled = run.count("★")
    empty = run.count("☆")
    return (
        f'<span class="stars" role="img" aria-label="{len(run)}점 만점에 {filled}점">'
        f'<span class="on">{"★" * filled}</span><span class="off">{"☆" * empty}</span></span>'
    )


def format_result(text: str) -> str:
    """모델 결과를 HTML 이스케이프한 뒤 별점만 색을 입힌 span으로 감싼다 (Markdown 문법은 유지)."""
    safe = html.escape(text, quote=False)
    return _STAR_RUN.sub(_stars_html, safe)

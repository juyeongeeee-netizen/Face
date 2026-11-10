"""OpenAI Vision 호출과 오류 분류."""

import openai
from openai import OpenAI

from prompts import FACE_NO, FACE_YES, NO_FACE_MESSAGE, USER_PROMPT, build_system_prompt

RETRY_MESSAGE = "다른 정면 사진으로 다시 시도해 주세요."
TRUNCATED_NOTE = "\n\n> ⚠️ 풀이가 길어 끝부분이 잘렸어요. '다시 분석하기'를 누르면 새로 받아볼 수 있어요."

# '얼굴 없음' 응답이 오면 한 번 더 물어본다. 모델이 보이는 얼굴을 가끔 NO로 답하는 경우가 있어서,
# 독립적으로 한 번 더 샘플링하면 오판이 크게 줄어든다. (진짜 얼굴 없는 사진은 짧은 응답 2회 비용)
NO_FACE_ATTEMPTS = 2

# 모델이 분석을 거절할 때 흔히 쓰는 표현 (결과 섹션이 없을 때만 검사)
REFUSAL_HINTS = ("죄송", "도와드릴 수 없", "I'm sorry", "I can't", "I cannot", "unable to")


class AnalysisError(Exception):
    """사용자에게 그대로 보여줄 안내 문구를 담은 분석 실패 예외."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NoFaceError(AnalysisError):
    """사진에서 얼굴을 찾지 못한 경우."""


def analyze_face(image_b64: str, api_key: str, model: str, style: str) -> str:
    """base64 이미지를 OpenAI Vision 모델에 보내 관상 풀이(Markdown)를 받아온다.

    '얼굴 없음' 판정이면 NO_FACE_ATTEMPTS번까지 다시 묻는다.
    실패하면 사용자용 문구를 담은 AnalysisError(또는 NoFaceError)를 던진다.
    """
    client = OpenAI(api_key=api_key, timeout=60, max_retries=1)
    for attempt in range(1, NO_FACE_ATTEMPTS + 1):
        try:
            return _parse_response(_request(client, image_b64, model, style))
        except NoFaceError:
            if attempt == NO_FACE_ATTEMPTS:
                raise
    raise AnalysisError(RETRY_MESSAGE)  # 도달하지 않음 (타입 검사용)


def _request(client: OpenAI, image_b64: str, model: str, style: str):
    """OpenAI Chat Completions를 1회 호출한다. SDK 예외는 사용자용 AnalysisError로 바꾼다."""
    try:
        return client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": build_system_prompt(style)},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": USER_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "low",
                            },
                        },
                    ],
                },
            ],
            max_tokens=1500,
            temperature=0.8,
        )
    except (openai.AuthenticationError, openai.PermissionDeniedError):
        raise AnalysisError("API 키를 확인해 주세요.")
    except openai.NotFoundError:
        raise AnalysisError(f"모델 '{model}'을(를) 사용할 수 없습니다. OPENAI_MODEL 설정을 확인해 주세요.")
    except openai.BadRequestError:
        raise AnalysisError(f"요청을 처리하지 못했습니다. {RETRY_MESSAGE}")
    except (openai.RateLimitError, openai.APIConnectionError, openai.APIStatusError):
        raise AnalysisError("잠시 후 다시 시도해 주세요.")
    except Exception:
        raise AnalysisError("예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")


def _parse_response(response) -> str:
    """응답에서 결과 텍스트를 꺼내고, 빈 응답·거절·얼굴 없음·잘림을 판별한다."""
    if not response.choices:
        raise AnalysisError(RETRY_MESSAGE)

    choice = response.choices[0]
    message = choice.message
    text = (message.content or "").strip()

    if getattr(message, "refusal", None) or choice.finish_reason == "content_filter" or not text:
        raise AnalysisError(RETRY_MESSAGE)

    first_line = text.splitlines()[0].strip().upper()
    if first_line.startswith(FACE_NO):
        raise NoFaceError(f"사진에서 얼굴을 찾지 못했어요. {NO_FACE_MESSAGE}.")

    section_start = text.find("## ")
    if section_start == -1:
        # 형식 없이 옛 안내 문구로만 답한 경우도 '얼굴 없음'으로 처리한다.
        if NO_FACE_MESSAGE in text:
            raise NoFaceError(f"사진에서 얼굴을 찾지 못했어요. {NO_FACE_MESSAGE}.")
        if any(hint in text for hint in REFUSAL_HINTS):
            raise AnalysisError(RETRY_MESSAGE)
        text = text.removeprefix(FACE_YES).strip()
    else:
        # 풀이 앞의 "FACE: YES" 줄과 사과·인사말("죄송하지만 … 대신 풀이해 드리겠습니다")은 잘라낸다.
        text = text[section_start:]

    # max_tokens에 걸려 응답이 중간에 끊긴 경우: 받은 부분은 보여주되 잘렸다는 사실을 알린다.
    if choice.finish_reason == "length":
        text += TRUNCATED_NOTE

    return text

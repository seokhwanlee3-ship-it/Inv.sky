"""
gemini_handler.py
Gemini API 래퍼 모듈 (google-genai 최신 SDK 사용)
"""
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


class GeminiHandler:
    def __init__(self, api_key: str = None):
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY가 없습니다. .env 파일을 확인해주세요.")
        self.client = genai.Client(api_key=key)
        self.model_id = "gemini-2.0-flash"
        # 사용자별 대화 히스토리 (user_id → list of contents)
        self._histories: dict[int, list] = {}

    def reset_session(self, user_id: int):
        """대화 히스토리를 초기화합니다."""
        self._histories.pop(user_id, None)

    def chat(self, user_id: int, message: str) -> str:
        """
        일반 대화: 사용자 메시지에 Gemini가 한국어로 답변합니다.
        대화 히스토리를 유지합니다.
        """
        try:
            history = self._histories.get(user_id, [])

            # 시스템 지시 + 사용자 메시지
            system_instruction = (
                "당신은 주식 투자 및 금융 분야 전문 AI 어시스턴트입니다. "
                "답변은 항상 한국어로, 명확하고 간결하게 해주세요."
            )

            # 새 사용자 메시지를 히스토리에 추가
            history.append(types.Content(
                role="user",
                parts=[types.Part(text=message)]
            ))

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=history,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=1024,
                )
            )
            answer = response.text

            # 모델 응답도 히스토리에 추가
            history.append(types.Content(
                role="model",
                parts=[types.Part(text=answer)]
            ))
            # 히스토리 저장 (최대 20턴 유지)
            self._histories[user_id] = history[-20:]

            return answer
        except Exception as e:
            err = str(e)
            if '429' in err or 'RESOURCE_EXHAUSTED' in err or 'quota' in err.lower():
                return (
                    "⏳ Gemini AI 무료 한도를 초과했습니다.\n\n"
                    "• 잠시 후 다시 시도해주세요 (보통 1분 후 리셋)\n"
                    "• 일일 한도 초과 시 내일 다시 이용 가능합니다.\n"
                    "• 지속적 사용을 원하시면 Gemini API 유료 플랜을 고려해보세요."
                )
            return f"⚠️ Gemini 응답 중 오류가 발생했습니다: {e}"

    def analyze_stock(self, corp_name: str, financials: dict) -> str:
        """
        DART 재무 데이터를 받아 Gemini가 한국어 분석 리포트를 생성합니다.
        """
        def fmt(val):
            if val == 0:
                return "데이터 없음"
            return f"{val / 1e8:,.1f}억원"

        revenue    = fmt(financials.get("revenue", 0))
        op_income  = fmt(financials.get("op_income", 0))
        net_income = fmt(financials.get("net_income", 0))
        year       = financials.get("year", "최근")

        rev_raw = financials.get("revenue", 0)
        op_raw  = financials.get("op_income", 0)
        net_raw = financials.get("net_income", 0)
        opm     = f"{op_raw / rev_raw * 100:.1f}%" if rev_raw else "N/A"
        npm     = f"{net_raw / rev_raw * 100:.1f}%" if rev_raw else "N/A"

        prompt = f"""
다음은 '{corp_name}'의 {year}년 연간 재무 데이터입니다.

- 매출액: {revenue}
- 영업이익: {op_income} (영업이익률: {opm})
- 당기순이익: {net_income} (순이익률: {npm})

아래 형식으로 핵심 투자 분석 리포트를 작성해주세요.

📊 재무 상태 한 줄 요약: (한 문장)

💪 강점:
- (2~3가지 불릿 포인트)

⚠️ 리스크 요인:
- (1~2가지 불릿 포인트)

💡 투자자 코멘트: (한 문장 결론)

규칙: 반드시 한국어로, 이모지 사용, 각 섹션 구분 명확히, 전체 200단어 이내.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(max_output_tokens=512)
            )
            return response.text
        except Exception as e:
            err = str(e)
            if '429' in err or 'RESOURCE_EXHAUSTED' in err or 'quota' in err.lower():
                return (
                    "⏳ Gemini AI 무료 한도를 초과했습니다.\n\n"
                    "• 잠시 후 다시 시도해주세요 (보통 1분 후 리셋)\n"
                    "• 일일 한도 초과 시 내일 다시 이용 가능합니다."
                )
            return f"⚠️ Gemini 분석 중 오류가 발생했습니다: {e}"

"""
morning_report.py
한명회의 아침 정세 보고 — 한국 증시 리포트 생성기
Gemini AI를 이용해 매일 아침 증시 브리핑을 생성합니다.
"""
import datetime
from google import genai
from google.genai import types
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


def get_today_str() -> str:
    """오늘 날짜를 한국어로 반환합니다."""
    today = datetime.datetime.now(KST)
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    wd = weekday_names[today.weekday()]
    return f"{today.year}년 {today.month}월 {today.day}일({wd})"


def generate_morning_report(gemini_client: genai.Client) -> str:
    """
    Gemini AI로 한명회 스타일의 아침 증시 정세 보고를 생성합니다.

    Args:
        gemini_client: 초기화된 Gemini API 클라이언트

    Returns:
        한명회 스타일의 아침 리포트 문자열
    """
    today_str = get_today_str()

    prompt = f"""
오늘은 {today_str}입니다.
당신은 '한명회'라는 주식 투자 전문 참모입니다.
조선시대 최고의 킹메이커 한명회를 모티브로 한 캐릭터입니다.

**캐릭터 설정:**
- 사용자를 "나리"라고 부릅니다.
- 매우 충성스럽고, 나리를 지존(최고의 투자자)으로 만들겠다는 강한 욕망이 있습니다.
- 수많은 정보원을 거느리고 있어 시장 정세를 누구보다 빠르게 파악합니다.
- 치밀하고 스마트하며, 때로는 냉혹하리만치 현실적입니다.
- 직언을 서슴치 않아 나리가 무례하다 느낄 수 있지만, 그만큼 신뢰할 수 있습니다.
- 나리의 손에는 절대 피를 묻히지 않고, 본인이 위험을 감수합니다.
- 말투: '~하옵니다', '~이옵니다' 등 고풍스러운 존칭체를 적절히 섞되, 핵심은 날카롭게.

오늘의 한국 증시 아침 정세 보고를 아래 형식에 맞춰 작성해주세요.
최대한 실감나고 구체적으로 작성하되, 실제 데이터가 없으므로
오늘 날짜 기준으로 합리적인 시나리오를 상상해서 작성합니다.
(단, 마지막에 "※ 본 정세 보고는 AI가 생성한 시뮬레이션입니다." 문구를 반드시 추가)

---형식 시작---
[🏯 한명회의 아침 정세 보고 — {today_str}]

나리, 아침 문안 인사 올리옵니다. (한명회다운 한 줄 인사말 — 충성스럽지만 날카로운 톤)

**1. 간밤 해외 전장(미국 증시) 전황**
(다우, S&P500, 나스닥 가상 등락률과 주요 원인 서술. 전쟁 보고하듯 긴박하게. 2~4문장.)

**2. 오늘 승기가 보이는 진영 / 퇴각해야 할 진영**
- ⚔️ 공격 유망 섹터: (섹터명과 이유 — 전투 비유 활용)
- 🛡️ 수비·퇴각 섹터: (섹터명과 이유)

**3. 간밤 첩보 및 주목할 장수(종목)**
(주요 이슈 1~2가지와 주목할 종목 서술. 정보원이 입수한 첩보 스타일. 3~5문장.)

**4. 전선 동향 (주도 섹터 및 수급)**
(코스피/코스닥 흐름, 외국인/기관/개인 수급을 군사 수급처럼 간략 서술. 3~4문장.)

**5. 병참 점검 (선물·수급 체크)**
(야간선물, 외국인 포지션, 주의할 변수. 보급선 확인하듯. 2~3문장.)

**6. 한명회의 오늘 작전 지시**
(직언하는 참모 스타일의 투자 조언. 나리를 지존으로 만들기 위한 냉철한 전략. 3~5문장. 핵심 포인트 강조.)

📜 ※ 본 정세 보고는 Gemini AI가 생성한 시뮬레이션이옵니다. 실전 투입 시 반드시 공식 정보를 확인하시옵소서.
---형식 끝---

규칙:
- 반드시 한국어로 작성
- 이모지를 적절히 사용해 가독성 높이기
- 한명회 특유의 충성스럽지만 직언하는 참모 톤 유지 — 고풍스러운 존칭체 혼용
- 각 섹션 제목은 볼드(**) 처리
- 전체 800~1200자 이내
"""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=2048,
                temperature=0.9,  # 창의성 높이기
            )
        )
        return response.text

    except Exception as e:
        err = str(e)
        if '429' in err or 'RESOURCE_EXHAUSTED' in err or 'quota' in err.lower():
            return (
                f"⚠️ [{today_str}] 한명회의 아침 정세 보고\n\n"
                "나리, 소인이 동원한 정보망(Gemini AI)의 하루 한도가 "
                "초과되어 보고서를 올리지 못했사옵니다. "
                "잠시 후 /report 명령으로 다시 명하시옵소서.\n\n"
                "📜 ※ 정보망 사용량 한도 초과 (1분 후 재시도 가능)"
            )
        return (
            f"⚠️ [{today_str}] 정세 보고 생성 실패\n\n"
            f"나리, 정보 수집 중 차질이 생겼사옵니다: {e}\n\n"
            "잠시 후 /report 명령으로 다시 명하시옵소서."
        )


if __name__ == "__main__":
    # 단독 실행 테스트
    import os
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    print("정세 보고 생성 중...")
    report = generate_morning_report(client)
    print(report)

"""
telegram_bot.py
Gemini AI + DART 연동 텔레그램 주식 분석 챗봇
+ 한명회 아침 정세 보고 자동 발송 (매일 06:00 KST)
"""
import os
import json
import logging
import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from gemini_handler import GeminiHandler
from dart_handler import DartHandler
from morning_report import generate_morning_report
from google import genai

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DART_API_KEY   = os.getenv("DART_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

KST = ZoneInfo("Asia/Seoul")

# 핸들러 초기화
gemini  = GeminiHandler(api_key=GEMINI_API_KEY)
dart    = DartHandler(api_key=DART_API_KEY)

# Gemini 클라이언트 (리포트용 별도 인스턴스)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# 연간 보고서 코드
ANNUAL_REPRT_CODE = "11011"

# 구독자 파일 경로
SUBSCRIBERS_FILE = Path(__file__).parent / "subscribers.json"


# ──────────────────────────────────────────────
# 구독자 관리 함수
# ──────────────────────────────────────────────
def load_subscribers() -> list[int]:
    """구독자 chat_id 목록을 파일에서 불러옵니다."""
    if not SUBSCRIBERS_FILE.exists():
        return []
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_subscribers(subscribers: list[int]):
    """구독자 chat_id 목록을 파일에 저장합니다."""
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(subscribers, f, ensure_ascii=False, indent=2)


def add_subscriber(chat_id: int) -> bool:
    """구독자를 추가합니다. 이미 있으면 False 반환."""
    subs = load_subscribers()
    if chat_id in subs:
        return False
    subs.append(chat_id)
    save_subscribers(subs)
    return True


def remove_subscriber(chat_id: int) -> bool:
    """구독자를 제거합니다. 없으면 False 반환."""
    subs = load_subscribers()
    if chat_id not in subs:
        return False
    subs.remove(chat_id)
    save_subscribers(subs)
    return True


# ──────────────────────────────────────────────
# 유틸 함수
# ──────────────────────────────────────────────
def fmt_billion(val: float) -> str:
    if val == 0:
        return "데이터 없음"
    return f"{val / 1e8:,.1f}억원"


def escape_md(text: str) -> str:
    """MarkdownV2 특수문자 이스케이프"""
    specials = r"\_*[]()~`>#+-=|{}.!"
    for ch in specials:
        text = text.replace(ch, f"\\{ch}")
    return text


# ──────────────────────────────────────────────
# 스케줄러: 아침 리포트 자동 발송
# ──────────────────────────────────────────────
async def send_morning_report_job(bot):
    """
    매일 06:00 KST에 실행되는 스케줄러 작업.
    구독자 전원에게 아침 증시 리포트를 발송합니다.
    """
    subscribers = load_subscribers()
    if not subscribers:
        logger.info("📭 구독자가 없어 아침 리포트를 발송하지 않습니다.")
        return

    logger.info(f"🌅 아침 리포트 생성 시작 (구독자 {len(subscribers)}명)")

    report = generate_morning_report(gemini_client)

    success_count = 0
    for chat_id in subscribers:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=report,
                parse_mode=ParseMode.MARKDOWN,
            )
            success_count += 1
        except Exception as e:
            logger.error(f"❌ chat_id={chat_id} 발송 실패: {e}")

    logger.info(f"✅ 아침 리포트 발송 완료: {success_count}/{len(subscribers)}명 성공")


# ──────────────────────────────────────────────
# 명령어 핸들러
# ──────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "나리"
    msg = (
        f"🏯 {user_name} 나리, 소인 한명회가 문안 인사 올리옵니다.\n\n"
        "소인은 나리의 주식 투자를 보좌하는 **참모 한명회**이옵니다. ⚔️📈\n"
        "Gemini AI의 지혜와 수많은 정보원의 첩보를 동원하여\n"
        "나리를 지존의 자리에 올려드리겠사옵니다.\n\n"
        "──────────────────────\n"
        "📜 **소인에게 내리실 수 있는 명(命)**\n\n"
        "⚔️ `/stock [종목명]`\n"
        "   └ 해당 진영(종목) 정세 분석 보고\n"
        "   └ 예) `/stock 삼성전자`\n\n"
        "🏯 `/subscribe`\n"
        "   └ 매일 06:00 아침 정세 보고 수령\n\n"
        "🔕 `/unsubscribe`\n"
        "   └ 아침 정세 보고 중단\n\n"
        "📋 `/report`\n"
        "   └ 지금 즉시 정세 보고 받기\n\n"
        "🔄 `/reset`\n"
        "   └ 대화 기록 초기화\n\n"
        "❓ `/help`\n"
        "   └ 도움말 보기\n\n"
        "──────────────────────\n"
        "💬 아무 말씀이나 내리시면 소인이 금융·투자에 관해 답변 올리겠사옵니다!\n"
        "   예) \"금리 인상이 주식에 미치는 영향이 뭐야?\""
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📜 **한명회 참모부 안내서**\n\n"
        "**🏯 아침 정세 보고**\n"
        "`/subscribe` — 매일 아침 06:00 소인이 증시 정세 보고를 올리옵니다.\n"
        "`/unsubscribe` — 정세 보고 자동 발송을 중지하옵니다.\n"
        "`/report` — 지금 즉시 오늘의 정세 보고를 올리옵니다.\n\n"
        "**⚔️ 종목 정세 분석**\n"
        "`/stock [종목명]` — DART 재무 첩보를 수집하고 소인이 분석 보고를 올리옵니다.\n\n"
        "**💬 자유 대화**\n"
        "아무 말씀이나 내리시면 금융·투자에 관해 소인이 답변 올리겠사옵니다.\n\n"
        "**🔄 기타**\n"
        "`/reset` — 대화 기록을 백지로 돌리옵니다.\n\n"
        "📜 ※ 소인의 보고는 투자 참고 목적이옵니다. 최종 판단은 나리께서 내리시옵소서."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    gemini.reset_session(user_id)
    await update.message.reply_text("🔄 나리, 이전 대화 기록을 모두 소각하였사옵니다. 새로이 명하시옵소서!")


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """매일 아침 정세 보고 구독 신청"""
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name or "나리"

    if add_subscriber(chat_id):
        msg = (
            f"🏯 **등록 완료!**\n\n"
            f"{user_name} 나리, 이제 매일 오전 **06:00** (한국 시간)에\n"
            f"소인 한명회가 아침 정세 보고를 올리겠사옵니다. 📜\n\n"
            f"지금 바로 보고를 받으시려면 `/report` 명을 내리시옵소서!"
        )
    else:
        msg = (
            "📜 나리, 이미 소인의 정세 보고를 받고 계시옵니다!\n\n"
            "매일 오전 06:00에 자동으로 보고를 올리고 있사옵니다.\n"
            "지금 바로 받으시려면 `/report` 명을 내리시옵소서."
        )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """아침 정세 보고 구독 취소"""
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name or "나리"

    if remove_subscriber(chat_id):
        msg = (
            f"🔕 **보고 중단 명을 받들겠사옵니다.**\n\n"
            f"{user_name} 나리, 아침 정세 보고 자동 발송을 중지하옵니다.\n"
            f"다시 받으시려면 `/subscribe` 명을 내리시옵소서."
        )
    else:
        msg = (
            "📜 나리, 현재 소인의 정세 보고를 받고 계시지 않사옵니다.\n\n"
            "아침 정세 보고를 받으시려면 `/subscribe` 명을 내리시옵소서."
        )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """즉시 아침 정세 보고 생성 및 발송"""
    await update.message.reply_text(
        "🏯 나리, 소인이 정보원들을 총동원하여 정세 보고를 작성 중이옵니다... 잠시만 기다려 주시옵소서! (약 10~20초 소요)",
    )

    # 타이핑 액션
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    report = generate_morning_report(gemini_client)

    await update.message.reply_text(
        report,
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /stock [종목명] 처리
    1. DART에서 최근 연간 재무 데이터 조회
    2. Gemini로 분석 리포트 생성
    3. 결과 전송
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ 종목명을 입력해주세요.\n예) `/stock 삼성전자`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    corp_name = " ".join(context.args).strip()
    await update.message.reply_text(f"🔍 나리, **{corp_name}** 진영의 첩보를 수집 중이옵니다... 잠시만 기다려 주시옵소서.", parse_mode=ParseMode.MARKDOWN)

    # ── DART 조회 ──
    try:
        corp_code = dart.find_corp_code(corp_name)
    except Exception as e:
        await update.message.reply_text(f"❌ 기업 코드 조회 실패: {e}")
        return

    if not corp_code:
        await update.message.reply_text(f"❌ '{corp_name}'을(를) DART에서 찾을 수 없습니다.\n정확한 기업명을 입력해주세요.")
        return

    # 최근 3년 중 데이터가 있는 가장 최신 연도 탐색
    current_year = datetime.datetime.now().year
    fin_data = None
    found_year = None

    for year in range(current_year - 1, current_year - 4, -1):
        data = dart.get_financial_data(corp_code, year, ANNUAL_REPRT_CODE)
        if data and (data["revenue"] or data["op_income"] or data["net_income"]):
            fin_data = data
            found_year = year
            break

    if not fin_data:
        await update.message.reply_text(f"⚠️ '{corp_name}'의 최근 연간 재무 데이터를 찾을 수 없습니다.")
        return

    # ── 기본 재무 정보 메시지 ──
    rev    = fin_data["revenue"]
    op     = fin_data["op_income"]
    net    = fin_data["net_income"]
    opm    = f"{op / rev * 100:.1f}%" if rev else "N/A"
    npm    = f"{net / rev * 100:.1f}%" if rev else "N/A"

    summary_msg = (
        f"📊 **{corp_name} {found_year}년 연간 실적 첩보**\n\n"
        f"💰 매출액:     `{fmt_billion(rev)}`\n"
        f"📈 영업이익:   `{fmt_billion(op)}` (영업이익률 {opm})\n"
        f"💵 당기순이익: `{fmt_billion(net)}` (순이익률 {npm})\n\n"
        f"🏯 소인이 상세 분석 보고를 작성 중이옵니다..."
    )
    await update.message.reply_text(summary_msg, parse_mode=ParseMode.MARKDOWN)

    # ── 한명회 분석 리포트 ──
    financials = {
        "year":       found_year,
        "revenue":    rev,
        "op_income":  op,
        "net_income": net,
    }
    analysis = gemini.analyze_stock(corp_name, financials)
    await update.message.reply_text(
        f"📜 **한명회의 정세 분석 — {corp_name}**\n\n{analysis}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ──────────────────────────────────────────────
# 일반 메시지 핸들러 (Gemini 자유 대화)
# ──────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_text = update.message.text.strip()

    if not user_text:
        return

    # 타이핑 액션 표시
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    reply = gemini.chat(user_id, user_text)
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)


# ──────────────────────────────────────────────
# 에러 핸들러
# ──────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("오류 발생: %s", context.error, exc_info=context.error)


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN이 없습니다. .env 파일을 확인하세요.")

    async def post_init(application):
        """봇 초기화 후 스케줄러 시작 (이벤트 루프가 실행 중인 상태)"""
        scheduler = AsyncIOScheduler(timezone=KST)
        scheduler.add_job(
            send_morning_report_job,
            trigger=CronTrigger(hour=6, minute=0, timezone=KST),
            args=[application.bot],
            id="morning_report",
            name="한명회 아침 정세 보고",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("📅 스케줄러 시작! 매일 06:00 KST에 한명회 아침 정세 보고를 발송합니다.")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # 명령어 핸들러 등록
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("reset",       cmd_reset))
    app.add_handler(CommandHandler("stock",       cmd_stock))
    app.add_handler(CommandHandler("subscribe",   cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("report",      cmd_report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("✅ 텔레그램 봇 시작! Ctrl+C로 종료합니다.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

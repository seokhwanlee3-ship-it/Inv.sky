"""
telegram_bot.py
Gemini AI + DART 연동 텔레그램 주식 분석 챗봇
"""
import os
import logging
import datetime
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

from gemini_handler import GeminiHandler
from dart_handler import DartHandler

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

# 핸들러 초기화
gemini  = GeminiHandler(api_key=GEMINI_API_KEY)
dart    = DartHandler(api_key=DART_API_KEY)

# 연간 보고서 코드
ANNUAL_REPRT_CODE = "11011"

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
# 명령어 핸들러
# ──────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "투자자"
    msg = (
        f"👋 안녕하세요, {user_name}님!\n\n"
        "저는 **Gemini AI** 기반 주식 분석 챗봇입니다. 🤖📈\n\n"
        "──────────────────────\n"
        "📌 **사용 가능한 명령어**\n\n"
        "📊 `/stock [종목명]`\n"
        "   └ DART 재무데이터 + Gemini 분석 리포트\n"
        "   └ 예) `/stock 삼성전자`\n\n"
        "🔄 `/reset`\n"
        "   └ 대화 히스토리 초기화\n\n"
        "❓ `/help`\n"
        "   └ 도움말 보기\n\n"
        "──────────────────────\n"
        "💬 일반 텍스트를 입력하면 Gemini AI와 자유롭게 대화할 수 있어요!\n"
        "   예) \"금리 인상이 주식에 미치는 영향이 뭐야?\""
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 **도움말**\n\n"
        "**주식 분석**\n"
        "`/stock [종목명]` — DART 최근 연간 재무 데이터를 조회하고 Gemini AI가 분석 리포트를 작성합니다.\n\n"
        "**일반 대화**\n"
        "아무 텍스트나 입력하면 Gemini AI가 금융·투자 관련 질문에 답변해드립니다.\n\n"
        "**기타**\n"
        "`/reset` — Gemini 대화 히스토리를 초기화합니다.\n\n"
        "⚠️ 본 챗봇은 투자 참고 목적으로만 사용하세요. 투자 손실에 대한 책임은 투자자 본인에게 있습니다."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    gemini.reset_session(user_id)
    await update.message.reply_text("🔄 대화 히스토리를 초기화했습니다. 새 대화를 시작하세요!")


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
    await update.message.reply_text(f"🔍 **{corp_name}** 데이터를 조회 중입니다... 잠시만 기다려주세요.", parse_mode=ParseMode.MARKDOWN)

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
        f"📊 **{corp_name} {found_year}년 연간 실적**\n\n"
        f"💰 매출액:     `{fmt_billion(rev)}`\n"
        f"📈 영업이익:   `{fmt_billion(op)}` (영업이익률 {opm})\n"
        f"💵 당기순이익: `{fmt_billion(net)}` (순이익률 {npm})\n\n"
        f"🤖 Gemini AI 분석 리포트를 생성 중입니다..."
    )
    await update.message.reply_text(summary_msg, parse_mode=ParseMode.MARKDOWN)

    # ── Gemini 분석 리포트 ──
    financials = {
        "year":       found_year,
        "revenue":    rev,
        "op_income":  op,
        "net_income": net,
    }
    analysis = gemini.analyze_stock(corp_name, financials)
    await update.message.reply_text(
        f"📝 **Gemini AI 분석 리포트 — {corp_name}**\n\n{analysis}",
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

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("stock", cmd_stock))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("✅ 텔레그램 봇 시작! Ctrl+C로 종료합니다.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

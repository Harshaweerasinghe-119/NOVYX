import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from database import get_connection, init_db

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

REFERRAL_REWARD = 100


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    telegram_user = update.effective_user

    if telegram_user is None or update.message is None:
        return

    user_id = telegram_user.id
    username = telegram_user.username or ""

    referrer_id = None

    if context.args and context.args[0].startswith("ref_"):
        try:
            candidate = int(context.args[0][4:])
            if candidate != user_id and candidate > 0:
                referrer_id = candidate
        except ValueError:
            pass

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT telegram_id FROM users WHERE telegram_id = ?",
            (user_id,),
        ).fetchone()

        if existing is None:
            # Only accept referrals from an already registered user.
            if referrer_id is not None:
                referrer = conn.execute(
                    "SELECT telegram_id FROM users WHERE telegram_id = ?",
                    (referrer_id,),
                ).fetchone()

                if referrer is None:
                    referrer_id = None

            conn.execute(
                """
                INSERT INTO users (telegram_id, username, referred_by)
                VALUES (?, ?, ?)
                """,
                (user_id, username, referrer_id),
            )

            if referrer_id is not None:
                conn.execute(
                    """
                    UPDATE users
                    SET balance = balance + ?
                    WHERE telegram_id = ?
                    """,
                    (REFERRAL_REWARD, referrer_id),
                )
                conn.execute(
                    """
                    INSERT INTO transactions
                    (telegram_id, amount, reason)
                    VALUES (?, ?, ?)
                    """,
                    (referrer_id, REFERRAL_REWARD, "Referral reward"),
                )

        else:
            conn.execute(
                "UPDATE users SET username = ? WHERE telegram_id = ?",
                (username, user_id),
            )

        row = conn.execute(
            "SELECT balance FROM users WHERE telegram_id = ?",
            (user_id,),
        ).fetchone()

        balance = row["balance"]

    await update.message.reply_text(
        "🚀 Welcome to NOVYX!\n\n"
        f"🪙 Your points: {balance}\n\n"
        "Commands:\n"
        "/balance - Check your points\n"
        "/referral - Get your referral link"
    )


async def balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if user is None or update.message is None:
        return

    with get_connection() as conn:
        row = conn.execute(
            "SELECT balance FROM users WHERE telegram_id = ?",
            (user.id,),
        ).fetchone()

    if row is None:
        await update.message.reply_text(
            "Please send /start first."
        )
        return

    await update.message.reply_text(
        f"🪙 Your NOVYX points: {row['balance']}"
    )


async def referral(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if user is None or update.message is None:
        return

    with get_connection() as conn:
        row = conn.execute(
            "SELECT telegram_id FROM users WHERE telegram_id = ?",
            (user.id,),
        ).fetchone()

    if row is None:
        await update.message.reply_text(
            "Please send /start first."
        )
        return

    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"

    await update.message.reply_text(
        "🔗 Your NOVYX referral link:\n"
        f"{link}\n\n"
        "Invite friends to earn points!"
    )


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN secret is missing."
        )

    init_db()

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("referral", referral))

    print("NOVYX bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()

import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters,
)
from database import DB
from config import (
    BOT_TOKEN, ADMIN_IDS, STARTING_COINS, AUCTION_START_VOTES,
    SKIP_VOTES, POLL_START_VOTES, CATEGORIES, ROSTER_SIZE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("bollywood-auction")
db = DB(os.getenv("DB_PATH", "data/auction.db"))


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def user_name(user) -> str:
    return user.full_name or str(user.id)


async def admin_only(update: Update) -> bool:
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔ This command is for bot admins only.")
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🏆 *BOLLYWOOD AUCTION & POLL BOT*\n\n"
        "👤 *PLAYER COMMANDS*\n"
        "/addteam Team Name — Register a team (300 coins)\n"
        "/myteam — Your balance and roster\n"
        "/leaderboard — Group rankings\n"
        "/list — Actress auction list\n"
        "/startauction — Vote to start (3 votes)\n"
        "/skip — Vote to skip (2 votes)\n"
        "/actress remove Name — Remove an actress\n"
        "Send a number to place a bid during an auction.\n\n"
        "📸 *POLL FINALE*\n"
        "/submit Actress Name Category — attach one photo\n"
        "Categories: " + ", ".join(CATEGORIES) + "\n"
        "/pollstart — Vote to launch all 5 categories (2 votes)\n\n"
        "🛠 *ADMIN COMMANDS*\n"
        "/addactress Name, Price, ImageURL\n"
        "/removeactress Name | /next | /team\n"
        "/endauction | /queue | /pollstart | /endpoll\n"
        "Use /help to see this menu again."
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def addteam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.effective_message.reply_text("Use: /addteam Team Name")
    name = " ".join(context.args).strip()
    ok, msg = db.add_team(
        update.effective_chat.id, update.effective_user.id,
        user_name(update.effective_user), name, STARTING_COINS,
    )
    await update.effective_message.reply_text(("✅ " if ok else "⚠️ ") + msg)


async def myteam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    team = db.team(update.effective_chat.id, update.effective_user.id)
    if not team:
        return await update.effective_message.reply_text("Register first with /addteam TeamName.")
    roster = db.roster(team["id"])
    names = "\n".join(f"• {x['name']} — {x['paid']} coins" for x in roster) or "No actresses drafted yet."
    await update.effective_message.reply_text(
        f"🏅 *{team['name']}*\n💰 Balance: *{team['coins']}* coins\n"
        f"👤 Owner: {team['owner_name']}\n🎬 Roster: {len(roster)}/{ROSTER_SIZE}\n{names}",
        parse_mode="Markdown",
    )


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.leaderboard(update.effective_chat.id)
    if not rows:
        return await update.effective_message.reply_text("No teams registered yet.")
    lines = [
        f"{i}. {r['name']} — {r['coins']} coins | {r['count']}/{ROSTER_SIZE} actresses"
        for i, r in enumerate(rows, 1)
    ]
    await update.effective_message.reply_text("🏆 *GROUP LEADERBOARD*\n" + "\n".join(lines), parse_mode="Markdown")


async def list_actresses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.actresses()
    if not rows:
        return await update.effective_message.reply_text("Auction list is empty. Ask an admin to add actresses.")
    lines = [f"• {r['name']} — base {r['price']} coins" for r in rows if not r["used"]]
    await update.effective_message.reply_text(
        "🎬 *AVAILABLE ACTRESSES*\n" + ("\n".join(lines) if lines else "All listed actresses have been auctioned."),
        parse_mode="Markdown",
    )


async def addactress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return
    raw = update.effective_message.text.partition(" ")[2]
    parts = [x.strip() for x in raw.split(",", 2)]
    if len(parts) != 3 or not parts[0] or not parts[1].isdigit() or int(parts[1]) < 1:
        return await update.effective_message.reply_text("Use: /addactress Name, Price, ImageURL")
    if not parts[2].startswith(("https://", "http://")):
        return await update.effective_message.reply_text("Please provide a valid http(s) image URL.")
    ok = db.add_actress(parts[0], int(parts[1]), parts[2])
    await update.effective_message.reply_text("✅ Actress added." if ok else "⚠️ That actress is already listed.")


async def removeactress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return
    name = " ".join(context.args).strip()
    if not name:
        return await update.effective_message.reply_text("Use: /removeactress Actress Name")
    await update.effective_message.reply_text("✅ Removed." if db.remove_actress(name) else "Actress not found.")


async def actress_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args[1:] if context.args and context.args[0].lower() == "remove" else context.args
    if not args:
        return await update.effective_message.reply_text("Use: /actress remove Actress Name")
    await update.effective_message.reply_text(
        "✅ Removed." if db.remove_actress(" ".join(args)) else "Actress not found."
    )


async def startauction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, uid = update.effective_chat.id, update.effective_user.id
    if is_admin(uid):
        db.clear_votes(chat, "start")
        return await launch_auction(update, context)
    count = db.vote(chat, uid, "start")
    if count >= AUCTION_START_VOTES:
        db.clear_votes(chat, "start")
        await launch_auction(update, context)
    else:
        await update.effective_message.reply_text(f"🗳 Auction start vote: {count}/{AUCTION_START_VOTES}")


async def launch_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    if db.active(chat):
        return await update.effective_message.reply_text("An auction is already active.")
    item = db.next_actress()
    if not item:
        return await update.effective_message.reply_text("No unused actresses. Admin: add more with /addactress.")
    db.begin_auction(chat, item["id"], item["price"])
    await send_current(context, chat)


async def send_current(context: ContextTypes.DEFAULT_TYPE, chat: int):
    item = db.current(chat)
    if not item:
        return
    caption = (
        f"🎬 *LIVE AUCTION*\n\nActress: *{item['name']}*\n"
        f"Current bid: *{item['current_bid']} coins*\n\n"
        "Send a higher number to bid. Use /skip to vote to skip."
    )
    try:
        await context.bot.send_photo(chat_id=chat, photo=item["image_url"], caption=caption, parse_mode="Markdown")
    except Exception:
        log.exception("Could not send auction image; sending text instead")
        await context.bot.send_message(chat_id=chat, text=caption, parse_mode="Markdown")


async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, uid = update.effective_chat.id, update.effective_user.id
    if not db.active(chat):
        return await update.effective_message.reply_text("There is no active auction.")
    if is_admin(uid):
        db.clear_votes(chat, "skip")
        return await advance(context, chat, update.effective_message)
    count = db.vote(chat, uid, "skip")
    if count >= SKIP_VOTES:
        db.clear_votes(chat, "skip")
        await advance(context, chat, update.effective_message)
    else:
        await update.effective_message.reply_text(f"🗳 Skip vote: {count}/{SKIP_VOTES}")


async def advance(context: ContextTypes.DEFAULT_TYPE, chat: int, message):
    result = db.finish_current(chat)
    if result:
        await message.reply_text(result)
    item = db.next_actress()
    if item:
        db.begin_auction(chat, item["id"], item["price"])
        await send_current(context, chat)
    else:
        db.clear_auction(chat)
        await message.reply_text("Auction list completed. Admin can use /endauction to evaluate finalists.")


async def next_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return
    if not db.active(update.effective_chat.id):
        return await update.effective_message.reply_text("No active auction.")
    db.clear_votes(update.effective_chat.id, "skip")
    await advance(context, update.effective_chat.id, update.effective_message)


async def bids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.text or not msg.text.strip().isdigit():
        return
    chat = update.effective_chat.id
    if not db.active(chat):
        return
    amount = int(msg.text.strip())
    team = db.team(chat, update.effective_user.id)
    if not team:
        return await msg.reply_text("Register a team first with /addteam TeamName.")
    item = db.current(chat)
    if not item:
        return
    if amount <= item["current_bid"]:
        return await msg.reply_text(f"Bid must be higher than {item['current_bid']} coins.")
    if amount > team["coins"]:
        return await msg.reply_text("Your team does not have enough coins for that bid.")
    if len(db.roster(team["id"])) >= ROSTER_SIZE:
        return await msg.reply_text("Your roster is already full (5/5).")
    if item["bidder"] == update.effective_user.id:
        return await msg.reply_text("You already hold the highest bid.")
    db.place_bid(chat, update.effective_user.id, amount)
    await msg.reply_text(f"🔨 {team['name']} bids {amount} coins!")


async def endauction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return
    db.clear_auction(update.effective_chat.id)
    rows = db.qualified(update.effective_chat.id)
    names = [f"• {r['name']} ({r['count']}/{ROSTER_SIZE})" for r in rows]
    await update.effective_message.reply_text(
        "🏁 Auction closed. Qualified teams (5/5):\n" + ("\n".join(names) if names else "No team has completed a 5-actress roster.")
    )


async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg.photo:
        return
    caption = msg.caption or ""
    bits = caption.split()
    if len(bits) < 3 or bits[0].split("@")[0].lower() != "/submit":
        return await msg.reply_text("Attach a photo with caption: /submit Actress Name Category")
    category = bits[-1].lower()
    if category not in CATEGORIES:
        return await msg.reply_text("Allowed categories: " + ", ".join(CATEGORIES))
    actress = " ".join(bits[1:-1])
    team = db.team(update.effective_chat.id, update.effective_user.id)
    if not team:
        return await msg.reply_text("Register your team first with /addteam.")
    roster = db.roster(team["id"])
    if len(roster) != ROSTER_SIZE:
        return await msg.reply_text("Only teams with a complete 5/5 roster can enter the finale.")
    if actress.lower() not in [x["name"].lower() for x in roster]:
        return await msg.reply_text("You can submit only one of your drafted actresses.")
    if db.actress_used_in_submission(team["id"], actress):
        return await msg.reply_text("Each drafted actress can be used only once across the five categories.")
    ok, result = db.submit(team["id"], category, actress, msg.photo[-1].file_id)
    await msg.reply_text(("✅ " if ok else "⚠️ ") + result)


async def queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return
    rows = db.submission_status(update.effective_chat.id)
    await update.effective_message.reply_text(
        "📋 *POLL FINALE STATUS*\n" + ("\n".join(rows) if rows else "No registered teams."),
        parse_mode="Markdown",
    )


async def pollstart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, uid = update.effective_chat.id, update.effective_user.id
    if db.polls_active(chat):
        return await update.effective_message.reply_text("Poll voting is already active.")
    if not is_admin(uid):
        count = db.vote(chat, uid, "poll")
        if count < POLL_START_VOTES:
            return await update.effective_message.reply_text(f"🗳 Poll launch vote: {count}/{POLL_START_VOTES}")
    submissions = db.all_submissions(chat)
    if not submissions:
        return await update.effective_message.reply_text("No finalist photo submissions yet.")
    db.clear_votes(chat, "poll")
    db.reset_poll_votes(chat)
    db.set_polls_active(chat, True)
    for entry in submissions:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🗳 Vote", callback_data=f"pv:{entry['id']}")
        ]])
        await context.bot.send_photo(
            chat_id=chat,
            photo=entry["file_id"],
            caption=f"🏆 {entry['team_name']}\n{entry['actress_name']} — {entry['category'].title()}\nVotes: 0",
            reply_markup=keyboard,
        )
    await update.effective_message.reply_text("✅ All submitted entries are posted. Voting is live!")


async def poll_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        submission_id = int(query.data.split(":")[1])
        ok, count = db.cast_poll_vote(update.effective_chat.id, query.from_user.id, submission_id)
        await query.answer("Vote counted!" if ok else "You already voted on this entry or voting is closed.", show_alert=not ok)
        if ok:
            entry = db.submission(submission_id)
            await query.edit_message_caption(
                caption=f"🏆 {entry['team_name']}\n{entry['actress_name']} — {entry['category'].title()}\nVotes: {count}",
                reply_markup=query.message.reply_markup,
            )
    except Exception:
        log.exception("Poll vote error")
        await query.answer("Voting unavailable.", show_alert=True)


async def endpoll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return
    chat = update.effective_chat.id
    db.set_polls_active(chat, False)
    rows = db.poll_results(chat)
    lines = [f"• {r['category'].title()}: {r['team_name']} — {r['votes']} votes" for r in rows]
    await update.effective_message.reply_text(
        "📊 *POLL RESULTS*\n" + ("\n".join(lines) if lines else "No votes recorded."),
        parse_mode="Markdown",
    )


async def teams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return
    rows = db.all_teams(update.effective_chat.id)
    lines = [f"• {r['name']} — {r['owner_name']} — {r['coins']} coins" for r in rows]
    await update.effective_message.reply_text("👥 *REGISTERED TEAMS*\n" + ("\n".join(lines) if lines else "No teams."), parse_mode="Markdown")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")
    application = Application.builder().token(BOT_TOKEN).build()
    handlers = [
        CommandHandler("start", start),
        CommandHandler("help", help_cmd),
        CommandHandler("addteam", addteam),
        CommandHandler("myteam", myteam),
        CommandHandler("leaderboard", leaderboard),
        CommandHandler("list", list_actresses),
        CommandHandler("addactress", addactress),
        CommandHandler("removeactress", removeactress),
        CommandHandler("startauction", startauction),
        CommandHandler("skip", skip),
        CommandHandler("next", next_cmd),
        CommandHandler("actress", actress_remove),
        CommandHandler("endauction", endauction),
        CommandHandler("queue", queue),
        CommandHandler("pollstart", pollstart),
        CommandHandler("endpoll", endpoll),
        CommandHandler("team", teams),
        MessageHandler(filters.PHOTO, submit),
        CallbackQueryHandler(poll_vote, pattern=r"^pv:\d+$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, bids),
    ]
    for handler in handlers:
        application.add_handler(handler)
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

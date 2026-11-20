import logging, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from database import DB
from config import BOT_TOKEN, ADMIN_IDS, STARTING_COINS, AUCTION_START_VOTES, SKIP_VOTES, POLL_START_VOTES, CATEGORIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log=logging.getLogger("auctionbot")
db=DB(os.getenv("DB_PATH","data/auction.db"))

def admin(uid): return uid in ADMIN_IDS
def mention(user): return user.full_name or str(user.id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏆 *BOLLYWOOD AUCTION & POLL BOT*\\n\\n"
        "Register: /addteam TeamName\\n"
        "Team: /myteam | /leaderboard | /list\\n"
        "Auction: /startauction (3 votes), /skip (2 votes)\\n"
        "Bid: send a number while an auction is active\\n"
        "Finale: /submit Actress Name Category\\n"
        "Categories: " + ", ".join(CATEGORIES) + "\\n"
        "Polls: /pollstart (2 votes)\\n\\n"
        "Admins: /addactress Name, Price, ImageURL | /next | /team | /endauction | /queue | /endpoll",
        parse_mode="Markdown")

async def addteam(update, context):
    if not context.args:
        return await update.message.reply_text("Use: /addteam Team Name")
    name=" ".join(context.args).strip()
    ok,msg=db.add_team(update.effective_chat.id, update.effective_user.id, mention(update.effective_user), name, STARTING_COINS)
    await update.message.reply_text(msg)

async def myteam(update, context):
    t=db.team(update.effective_chat.id, update.effective_user.id)
    if not t: return await update.message.reply_text("Pehle /addteam TeamName karein.")
    roster=db.roster(t["id"])
    await update.message.reply_text(f"🏅 {t['name']}\\nCoins: {t['coins']}\\nPlayers: {t['owner_name']}\\nActresses ({len(roster)}/5): "+(", ".join(x["name"] for x in roster) or "None"))

async def leaderboard(update, context):
    rows=db.leaderboard(update.effective_chat.id)
    if not rows: return await update.message.reply_text("Abhi koi team registered nahi hai.")
    s="🏆 *LEADERBOARD*\\n"+ "\\n".join(f"{i}. {r['name']} — {r['coins']} coins | {r['count']}/5" for i,r in enumerate(rows,1))
    await update.message.reply_text(s,parse_mode="Markdown")

async def list_actresses(update, context):
    rows=db.actresses()
    if not rows: return await update.message.reply_text("Actress list empty hai.")
    await update.message.reply_text("📸 *AUCTION LIST*\\n"+ "\\n".join(f"• {r['name']} — base {r['price']} coins" for r in rows),parse_mode="Markdown")

async def addactress(update, context):
    if not admin(update.effective_user.id): return await update.message.reply_text("Admin only.")
    raw=update.message.text.partition(" ")[2]
    parts=[x.strip() for x in raw.split(",",2)]
    if len(parts)!=3 or not parts[1].isdigit(): return await update.message.reply_text("Use: /addactress Name, Price, ImageURL")
    if not parts[2].startswith(("https://","http://")): return await update.message.reply_text("Valid image URL dein.")
    db.add_actress(parts[0],int(parts[1]),parts[2])
    await update.message.reply_text(f"Added: {parts[0]}")

async def startauction(update, context):
    chat=update.effective_chat.id; uid=update.effective_user.id
    if admin(uid):
        await launch_auction(update, context); return
    n=db.vote(chat,uid,"start")
    if n>=AUCTION_START_VOTES:
        await launch_auction(update,context)
    else: await update.message.reply_text(f"Start vote recorded: {n}/{AUCTION_START_VOTES}")

async def launch_auction(update,context):
    chat=update.effective_chat.id
    if db.active(chat): return await update.effective_message.reply_text("Auction already active.")
    item=db.next_actress()
    if not item: return await update.effective_message.reply_text("Auction list empty. Admin /addactress kare.")
    db.begin_auction(chat,item["id"],item["price"])
    await send_current(context,chat)

async def send_current(context,chat):
    a=db.current(chat)
    if not a: return
    text=f"🎬 *LIVE AUCTION*\\n\\nActress: *{a['name']}*\\nBase/current bid: {a['current_bid']} coins\\n\\nBid bhejne ke liye number type karein. /skip se vote karein."
    try:
        await context.bot.send_photo(chat_id=chat,photo=a["image_url"],caption=text,parse_mode="Markdown")
    except Exception:
        await context.bot.send_message(chat_id=chat,text=text,parse_mode="Markdown")

async def skip(update,context):
    chat=update.effective_chat.id
    if admin(update.effective_user.id): return await advance(context,chat,update.effective_message)
    n=db.vote(chat,update.effective_user.id,"skip")
    if n>=SKIP_VOTES: await advance(context,chat,update.effective_message)
    else: await update.message.reply_text(f"Skip vote: {n}/{SKIP_VOTES}")

async def advance(context,chat,msg):
    result=db.finish_current(chat)
    if result:
        await msg.reply_text(result)
    item=db.next_actress()
    if item:
        db.begin_auction(chat,item["id"],item["price"])
        await send_current(context,chat)
    else:
        db.clear_auction(chat)
        await msg.reply_text("Auction list complete. Admin /endauction chala sakta hai.")

async def next_cmd(update,context):
    if not admin(update.effective_user.id): return await update.message.reply_text("Admin only.")
    await advance(context,update.effective_chat.id,update.message)

async def bids(update,context):
    if not update.message or not update.message.text or not update.message.text.strip().isdigit(): return
    chat=update.effective_chat.id
    if not db.active(chat): return
    amount=int(update.message.text.strip())
    t=db.team(chat,update.effective_user.id)
    if not t: return await update.message.reply_text("Bid karne se pehle /addteam TeamName karein.")
    a=db.current(chat)
    if not a: return
    if amount<=a["current_bid"]: return await update.message.reply_text(f"Bid current {a['current_bid']} se zyada honi chahiye.")
    if amount>t["coins"]: return await update.message.reply_text("Aapke paas itne coins nahi hain.")
    if len(db.roster(t["id"]))>=5: return await update.message.reply_text("Team ke 5 actresses already complete hain.")
    db.place_bid(chat,update.effective_user.id,amount)
    await update.message.reply_text(f"🔨 {t['name']} ne {amount} coins bid kiye!")

async def actress_remove(update,context):
    if not context.args: return await update.message.reply_text("Use: /actress remove Actress Name")
    args=context.args
    if args[0].lower()=="remove": args=args[1:]
    if not args: return await update.message.reply_text("Actress name missing.")
    ok=db.remove_actress(" ".join(args))
    await update.message.reply_text("Removed." if ok else "Actress not found.")

async def endauction(update,context):
    if not admin(update.effective_user.id): return await update.message.reply_text("Admin only.")
    db.clear_auction(update.effective_chat.id)
    rows=db.qualified(update.effective_chat.id)
    names=[f"{r['name']} ({r['count']}/5)" for r in rows]
    await update.message.reply_text("🏁 Auction ended. Qualified teams (5/5):\\n"+("\\n".join(names) if names else "No team has completed all 5 slots."))

async def submit(update,context):
    if not update.message.photo: return await update.message.reply_text("Photo ke saath caption dein: /submit Actress Name Category")
    raw=update.message.caption or ""
    bits=raw.split()
    if len(bits)<3 or bits[0].lower()!="/submit": return await update.message.reply_text("Photo caption: /submit Actress Name Category")
    category=bits[-1].lower()
    if category not in CATEGORIES: return await update.message.reply_text("Categories: "+", ".join(CATEGORIES))
    actress=" ".join(bits[1:-1])
    t=db.team(update.effective_chat.id,update.effective_user.id)
    if not t: return await update.message.reply_text("Pehle team register karein.")
    roster=db.roster(t["id"])
    if actress.lower() not in [x["name"].lower() for x in roster]:
        return await update.message.reply_text("Sirf apni drafted actresses mein se submit karein.")
    fid=update.message.photo[-1].file_id
    ok,msg=db.submit(t["id"],category,actress,fid)
    await update.message.reply_text(msg)

async def queue(update,context):
    if not admin(update.effective_user.id): return await update.message.reply_text("Admin only.")
    rows=db.submission_status(update.effective_chat.id)
    await update.message.reply_text("📋 POLL FINALE\\n"+("\\n".join(rows) if rows else "No submissions yet."))

async def pollstart(update,context):
    chat=update.effective_chat.id; uid=update.effective_user.id
    if not admin(uid):
        n=db.vote(chat,uid,"poll")
        if n<POLL_START_VOTES: return await update.message.reply_text(f"Poll launch vote: {n}/{POLL_START_VOTES}")
    submissions=db.all_submissions(chat)
    if not submissions: return await update.message.reply_text("No submitted photos.")
    db.reset_poll_votes(chat)
    for s in submissions:
        keyboard=InlineKeyboardMarkup([[InlineKeyboardButton("❤️ Vote",callback_data=f"pv:{s['id']}")]])
        await context.bot.send_photo(chat_id=chat,photo=s["file_id"],caption=f"🏆 {s['team_name']}\\n{ s['actress_name'] } — {s['category'].title()}\\nVotes: 0",reply_markup=keyboard)
    db.set_polls_active(chat,True)
    await update.message.reply_text("All submitted category entries posted. Voting is live!")

async def poll_vote(update,context):
    q=update.callback_query
    try:
        sid=int(q.data.split(":")[1])
        ok,count=db.cast_poll_vote(update.effective_chat.id,q.from_user.id,sid)
        await q.answer("Vote counted!" if ok else "You already voted here.",show_alert=not ok)
        if ok:
            s=db.submission(sid)
            await q.edit_message_caption(caption=f"🏆 {s['team_name']}\\n{s['actress_name']} — {s['category'].title()}\\nVotes: {count}",reply_markup=q.message.reply_markup)
    except Exception as e:
        log.exception("poll vote error"); await q.answer("Voting unavailable.",show_alert=True)

async def endpoll(update,context):
    if not admin(update.effective_user.id): return await update.message.reply_text("Admin only.")
    db.set_polls_active(update.effective_chat.id,False)
    rows=db.poll_results(update.effective_chat.id)
    await update.message.reply_text("📊 POLL RESULTS\\n"+("\\n".join(f"{r['category']}: {r['team_name']} — {r['votes']} votes" for r in rows) if rows else "No votes recorded."))

async def teams(update,context):
    if not admin(update.effective_user.id): return await update.message.reply_text("Admin only.")
    rows=db.all_teams(update.effective_chat.id)
    await update.message.reply_text("👥 TEAMS\\n"+("\\n".join(f"{r['name']} — {r['owner_name']} — {r['coins']} coins" for r in rows) if rows else "No teams."))

def main():
    if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN environment variable missing")
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("addteam",addteam))
    app.add_handler(CommandHandler("myteam",myteam))
    app.add_handler(CommandHandler("leaderboard",leaderboard))
    app.add_handler(CommandHandler("list",list_actresses))
    app.add_handler(CommandHandler("addactress",addactress))
    app.add_handler(CommandHandler("startauction",startauction))
    app.add_handler(CommandHandler("skip",skip))
    app.add_handler(CommandHandler("next",next_cmd))
    app.add_handler(CommandHandler("actress",actress_remove))
    app.add_handler(CommandHandler("endauction",endauction))
    app.add_handler(CommandHandler("submit",submit,filters=filters.PHOTO))
    app.add_handler(CommandHandler("queue",queue))
    app.add_handler(CommandHandler("pollstart",pollstart))
    app.add_handler(CommandHandler("endpoll",endpoll))
    app.add_handler(CommandHandler("team",teams))
    app.add_handler(CallbackQueryHandler(poll_vote,pattern=r"^pv:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,bids))
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__": main()

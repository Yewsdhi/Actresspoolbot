
import os, logging, random, sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode
from html import escape
from urllib.parse import quote
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN=os.getenv("BOT_TOKEN","")
ADMINS={int(x) for x in os.getenv("ADMIN_IDS","").replace(" ","").split(",") if x.isdigit()}
DB_PATH=os.getenv("DB_PATH","/tmp/actress_arena.db")
CATEGORIES=["traditional","western","redcarpet","casual","cinematic"]
log=logging.getLogger("actress_arena")
os.makedirs(os.path.dirname(DB_PATH) or ".",exist_ok=True)
db=sqlite3.connect(DB_PATH,check_same_thread=False)
db.row_factory=sqlite3.Row

def run(sql,args=()):
    cur=db.execute(sql,args); db.commit(); return cur
def init():
    run("CREATE TABLE IF NOT EXISTS teams(id INTEGER PRIMARY KEY,chat INTEGER,owner INTEGER,name TEXT,coins INTEGER,UNIQUE(chat,owner),UNIQUE(chat,name))")
    run("CREATE TABLE IF NOT EXISTS actresses(id INTEGER PRIMARY KEY,name TEXT UNIQUE,price INTEGER,image TEXT,used INTEGER DEFAULT 0)")
    try:
        run("ALTER TABLE actresses ADD COLUMN profile_url TEXT")
    except sqlite3.OperationalError:
        pass
    # Built-in starter catalogue: image field links to a Wikimedia Commons image search;
    # profile_url links to the actress's Wikipedia biography. No third-party image is hotlinked.
    bollywood_seed = [
        'Alia Bhatt',
        'Deepika Padukone',
        'Kareena Kapoor Khan',
        'Priyanka Chopra Jonas',
        'Katrina Kaif',
        'Anushka Sharma',
        'Shraddha Kapoor',
        'Kiara Advani',
        'Kriti Sanon',
        'Kangana Ranaut',
        'Vidya Balan',
        'Taapsee Pannu',
        'Bhumi Pednekar',
        'Parineeti Chopra',
        'Sonakshi Sinha',
        'Janhvi Kapoor',
        'Sara Ali Khan',
        'Ananya Panday',
        'Disha Patani',
        'Rashmika Mandanna',
        'Madhuri Dixit',
        'Aishwarya Rai Bachchan',
        'Rani Mukerji',
        'Kajol',
        'Preity Zinta',
        'Shilpa Shetty',
        'Sushmita Sen',
        'Bipasha Basu',
        'Lara Dutta',
        "Genelia D'Souza",
        'Sonam Kapoor',
        'Jacqueline Fernandez',
        'Nora Fatehi',
        'Mrunal Thakur',
        'Pooja Hegde',
        'Yami Gautam',
        "Ileana D'Cruz",
        'Kajal Aggarwal',
        'Tamannaah Bhatia',
        'Rakul Preet Singh',
        'Shriya Saran',
        'Nushrratt Bharuccha',
        'Huma Qureshi',
        'Richa Chadha',
        'Swara Bhasker',
        'Amrita Rao',
        'Ayesha Takia',
        'Dia Mirza',
        'Neha Dhupia',
        'Esha Gupta',
        'Raveena Tandon',
        'Twinkle Khanna',
        'Urmila Matondkar',
        'Tabu',
        'Manisha Koirala',
        'Sonali Bendre',
        'Karishma Kapoor',
        'Juhi Chawla',
        'Mahima Chaudhry',
        'Namrata Shirodkar',
        'Zeenat Aman',
        'Rekha',
        'Dimple Kapadia',
        'Jaya Bachchan',
        'Shabana Azmi',
        'Smita Patil',
        'Poonam Dhillon',
        'Meenakshi Seshadri',
        'Amrita Singh',
        'Farah Naaz',
        'Radhika Apte',
        'Radhika Madan',
        'Sanya Malhotra',
        'Fatima Sana Shaikh',
        'Konkona Sen Sharma',
        'Tillotama Shome',
        'Shefali Shah',
        'Neena Gupta',
        'Rasika Dugal',
        'Mona Singh',
        'Avneet Kaur',
        'Palak Tiwari',
        'Khushi Kapoor',
        'Suhana Khan',
        'Tara Sutaria',
        'Pranitha Subhash',
        'Aditi Rao Hydari',
        'Sobhita Dhulipala',
        'Sai Pallavi',
        'Nimrat Kaur',
        'Shanaya Kapoor',
        'Mouni Roy',
        'Aahana Kumra',
        'Prachi Desai',
        'Amisha Patel',
        'Ritu Varma',
        'Kriti Kharbanda',
        'Madhurima Tuli',
        'Sakshi Malik',
        'Manushi Chhillar'
    ]
    for actress_name in bollywood_seed:
        wiki_title = quote(actress_name.replace(" ", "_"), safe="_()'")
        profile = "https://en.wikipedia.org/wiki/" + wiki_title
        photo_search = "https://commons.wikimedia.org/wiki/Special:MediaSearch?type=image&search=" + quote(actress_name + " actress")
        run("INSERT OR IGNORE INTO actresses(name,price,image,profile_url) VALUES(?,?,?,?)",
            (actress_name, 100, photo_search, profile))
    run("CREATE TABLE IF NOT EXISTS roster(team INTEGER,actress INTEGER,paid INTEGER,UNIQUE(team,actress))")
    run("CREATE TABLE IF NOT EXISTS auction(chat INTEGER PRIMARY KEY,actress INTEGER,bid INTEGER,bidder INTEGER)")
    run("CREATE TABLE IF NOT EXISTS votes(chat INTEGER,user INTEGER,kind TEXT,UNIQUE(chat,user,kind))")
    run("CREATE TABLE IF NOT EXISTS scores(user INTEGER PRIMARY KEY,points INTEGER DEFAULT 0,streak INTEGER DEFAULT 0)")
    run("CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY,answer TEXT,hint TEXT,image TEXT,active INTEGER DEFAULT 1)")
    run("CREATE TABLE IF NOT EXISTS daily(chat INTEGER PRIMARY KEY,question INTEGER,day TEXT)")
    run("CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY,team INTEGER,category TEXT,actress TEXT,file TEXT,UNIQUE(team,category))")
    run("CREATE TABLE IF NOT EXISTS pollvotes(submission INTEGER,user INTEGER,UNIQUE(submission,user))")
    run("CREATE TABLE IF NOT EXISTS polls(chat INTEGER PRIMARY KEY,active INTEGER DEFAULT 0)")
init()
def is_admin(uid): return uid in ADMINS
def team(chat,uid): 
    r=run("SELECT * FROM teams WHERE chat=? AND owner=?",(chat,uid)).fetchone(); return r
def roster(tid):
    return run("SELECT a.name,r.paid FROM roster r JOIN actresses a ON a.id=r.actress WHERE r.team=?",(tid,)).fetchall()
def menu():
    return InlineKeyboardMarkup([
      [InlineKeyboardButton("➕ Add Team",callback_data="cmd:addteam"),InlineKeyboardButton("👥 Teams",callback_data="cmd:teams")],
      [InlineKeyboardButton("👤 My Team",callback_data="profile"),InlineKeyboardButton("🏆 Leaderboard",callback_data="leader")],
      [InlineKeyboardButton("🔗 All Actress Links",callback_data="list"),InlineKeyboardButton("🎯 Guess",callback_data="guess")],
      [InlineKeyboardButton("🎁 Daily",callback_data="daily"),InlineKeyboardButton("🔨 Start Auction",callback_data="cmd:startauction")],
      [InlineKeyboardButton("⏭ Skip Auction",callback_data="cmd:skip"),InlineKeyboardButton("📋 Queue",callback_data="cmd:queue")],
      [InlineKeyboardButton("🗳 Start Poll",callback_data="cmd:pollstart"),InlineKeyboardButton("📊 End Poll",callback_data="cmd:endpoll")],
      [InlineKeyboardButton("❓ All Commands",callback_data="help")]
    ])
async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
    await u.effective_message.reply_text("👑 ACTRESS ARENA\n\nWelcome! Play actress guessing, join live auctions, collect coins and compete with friends.\n\nChoose a menu:",reply_markup=menu())
async def buttons(u,c):
    q=u.callback_query; await q.answer()
    if q.data.startswith("cmd:"):
        cmd=q.data.split(":",1)[1]
        await q.message.reply_text("Use /"+cmd+" in this chat.")
    elif q.data=="help":
        await q.message.reply_text("/addteam Name · /myteam · /teams · /leaderboard · /list\n/guess · /daily · /startauction · /skip\nAdmin: /addactress Name, Price, ImageURL\n/addquestion Answer, Hint, ImageURL\n/next · /endauction · /queue · /pollstart · /endpoll")
    elif q.data=="guess": await guess(u,c)
    elif q.data=="daily": await daily(u,c)
    elif q.data=="auction": await q.message.reply_text("Join/register first: /addteam Royal\nThen vote: /startauction (3 votes).")
    elif q.data=="profile": await myteam(u,c)
    elif q.data=="leader": await leaderboard(u,c)
    elif q.data=="list": await list_actresses(u,c)
    elif q.data=="finale": await q.message.reply_text("Finale: submit a photo with caption /submit Actress Name Category. Categories: "+", ".join(CATEGORIES))
async def addteam(u,c):
    if not c.args: return await u.effective_message.reply_text("Use: /addteam Royal")
    name=" ".join(c.args)
    try:
        run("INSERT INTO teams(chat,owner,name,coins) VALUES(?,?,?,300)",(u.effective_chat.id,u.effective_user.id,name))
        await u.effective_message.reply_text(f"✅ Team {name} registered! 300 coins added.")
    except sqlite3.IntegrityError: await u.effective_message.reply_text("You already have a team or that team name is taken.")
async def teams(u,c):
    rows=run("SELECT t.name,t.coins,COUNT(r.actress) n FROM teams t LEFT JOIN roster r ON r.team=t.id WHERE t.chat=? GROUP BY t.id ORDER BY t.name COLLATE NOCASE",(u.effective_chat.id,)).fetchall()
    await u.effective_message.reply_text("👥 REGISTERED TEAMS\\n"+("\\n".join(f"{i}. {x['name']} — {x['n']}/5 actresses · {x['coins']} coins" for i,x in enumerate(rows,1)) if rows else "No teams registered yet. Use /addteam Team Name."))

async def myteam(u,c):
    t=team(u.effective_chat.id,u.effective_user.id)
    if not t: return await u.effective_message.reply_text("Register first: /addteam Royal")
    r=roster(t["id"])
    await u.effective_message.reply_text(f"👤 {t['name']}\n💰 Coins: {t['coins']}\n🎬 Actresses: {len(r)}/5\n"+("\n".join(x["name"] for x in r) if r else "No actresses drafted yet."))
async def leaderboard(u,c):
    rows=run("SELECT t.name,t.coins,COUNT(r.actress) n FROM teams t LEFT JOIN roster r ON r.team=t.id WHERE t.chat=? GROUP BY t.id ORDER BY n DESC,t.coins DESC",(u.effective_chat.id,)).fetchall()
    await u.effective_message.reply_text("🏆 LEADERBOARD\n"+("\n".join(f"{i}. {x['name']} — {x['n']}/5 · {x['coins']} coins" for i,x in enumerate(rows,1)) if rows else "No teams yet."))
async def list_actresses(u,c):
    rows=run("SELECT name,price,image,used,profile_url FROM actresses ORDER BY name COLLATE NOCASE").fetchall()
    if not rows:
        return await u.effective_message.reply_text("🎬 Actress list is empty. Admin: /addactress Name, Price, ImageURL")
    lines=[]
    for i,x in enumerate(rows,1):
        name=escape(x["name"])
        profile=(x["profile_url"] or "").strip()
        photo=(x["image"] or "").strip()
        status=" · Auctioned" if x["used"] else " · Available"
        links=[]
        if profile.startswith(("https://","http://")):
            links.append(f'<a href="{escape(profile, quote=True)}">Profile</a>')
        if photo.startswith(("https://","http://")):
            links.append(f'<a href="{escape(photo, quote=True)}">Photo search</a>')
        suffix=(" · "+" | ".join(links)) if links else " · No links"
        lines.append(f"{i}. <b>{name}</b> — {x['price']} coins{status}{suffix}")
    chunks=[]
    current="🎬 <b>BOLLYWOOD ACTRESS DATABASE</b>\\n"
    for line in lines:
        if len(current)+len(line)+1>3500:
            chunks.append(current)
            current="🎬 <b>ACTRESS DATABASE (continued)</b>\\n"
        current+=line+"\\n"
    if current.strip(): chunks.append(current)
    for chunk in chunks:
        await u.effective_message.reply_text(chunk,parse_mode=ParseMode.HTML,disable_web_page_preview=True)
async def addactress(u,c):
    if not is_admin(u.effective_user.id): return await u.effective_message.reply_text("Admin only.")
    p=u.effective_message.text.partition(" ")[2].split(",",2)
    if len(p)!=3 or not p[1].strip().isdigit() or int(p[1].strip()) < 1: return await u.effective_message.reply_text("Use: /addactress Name, Price (minimum 1), ImageURL")
    actress_name=p[0].strip()
    profile="https://en.wikipedia.org/wiki/"+quote(actress_name.replace(" ","_"),safe="_()'")
    run("INSERT OR IGNORE INTO actresses(name,price,image,profile_url) VALUES(?,?,?,?)",
        (actress_name,int(p[1]),p[2].strip(),profile))
    await u.effective_message.reply_text("Actress added (if name was new).")
async def addquestion(u,c):
    if not is_admin(u.effective_user.id): return await u.effective_message.reply_text("Admin only.")
    p=u.effective_message.text.partition(" ")[2].split(",",2)
    if len(p)!=3: return await u.effective_message.reply_text("Use: /addquestion Answer, Hint, ImageURL")
    run("INSERT INTO questions(answer,hint,image) VALUES(?,?,?)",tuple(x.strip() for x in p))
    await u.effective_message.reply_text("Guess question added.")
async def guess(u,c):
    q=run("SELECT * FROM questions WHERE active=1 ORDER BY RANDOM() LIMIT 1").fetchone()
    if not q: return await u.effective_message.reply_text("No guess questions yet. Admin can add with /addquestion Answer, Hint, ImageURL")
    c.user_data["guess_answer"]=q["answer"].lower()
    c.user_data["guess_hint"]=q["hint"]
    c.user_data["guess_image"]=q["image"]
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("💡 Hint",callback_data="hint:"+str(q["id"]))]])
    try: await u.effective_message.reply_photo(q["image"],caption="Who is this actress? Reply with her name. First correct answer earns 10 coins!",reply_markup=kb)
    except: await u.effective_message.reply_text("Who is this actress? Hint button below.",reply_markup=kb)
async def daily(u,c):
    await guess(u,c)
async def hint_button(u,c):
    q=u.callback_query; await q.answer()
    qid=int(q.data.split(":")[1])
    row=run("SELECT hint FROM questions WHERE id=?",(qid,)).fetchone()
    await q.message.reply_text("💡 Hint: "+(row["hint"] if row else "Hint unavailable.")) 
async def text_guess(u,c):
    ans=c.user_data.get("guess_answer")
    if not ans or not u.message or not u.message.text: return
    if u.message.text.strip().lower()==ans:
        c.user_data.pop("guess_answer",None)
        uid=u.effective_user.id
        run("INSERT INTO scores(user,points,streak) VALUES(?,10,1) ON CONFLICT(user) DO UPDATE SET points=points+10,streak=streak+1",(uid,))
        await u.message.reply_text("🎉 Correct! +10 points. Well played!")
async def startauction(u,c):
    chat=u.effective_chat.id; uid=u.effective_user.id
    if not is_admin(uid):
        run("INSERT OR IGNORE INTO votes VALUES(?,?,?)",(chat,uid,"start"))
        n=run("SELECT COUNT(*) n FROM votes WHERE chat=? AND kind='start'",(chat,)).fetchone()["n"]
        if n<3: return await u.effective_message.reply_text(f"Auction start vote: {n}/3")
        run("DELETE FROM votes WHERE chat=? AND kind='start'",(chat,))
    if run("SELECT 1 FROM auction WHERE chat=?",(chat,)).fetchone(): return await u.effective_message.reply_text("Auction already active.")
    a=run("SELECT * FROM actresses WHERE used=0 ORDER BY id LIMIT 1").fetchone()
    if not a: return await u.effective_message.reply_text("No available actresses. Admin add with /addactress.")
    run("INSERT OR REPLACE INTO auction VALUES(?,?,?,NULL)",(chat,a["id"],max(0,a["price"]-1)))
    await show_auction(c,chat)
async def show_auction(c,chat):
    a=run("SELECT x.*,v.bid FROM auction v JOIN actresses x ON x.id=v.actress WHERE v.chat=?",(chat,)).fetchone()
    if not a:return
    msg=f"🔨 LIVE AUCTION\n{a['name']}\nCurrent bid: {a['bid']} coins\nSend a higher number to bid."
    try: await c.bot.send_photo(chat,a["image"],caption=msg)
    except: await c.bot.send_message(chat,msg)
async def bids(u,c):
    if not u.message or not u.message.text: return
    if not u.message.text.strip().isdigit(): return
    chat=u.effective_chat.id; a=run("SELECT * FROM auction WHERE chat=?",(chat,)).fetchone()
    if not a:return
    t=team(chat,u.effective_user.id)
    if not t:return await u.message.reply_text("Register first: /addteam TeamName")
    amount=int(u.message.text.strip())
    if amount<=a["bid"] or amount>t["coins"]:return await u.message.reply_text("Bid must be higher than current bid and within your coins.")
    if len(roster(t["id"]))>=5:return await u.message.reply_text("Roster already full (5/5).")
    run("UPDATE auction SET bid=?,bidder=? WHERE chat=?",(amount,u.effective_user.id,chat))
    await u.message.reply_text(f"🔨 {t['name']} bid {amount} coins.")
async def skip(u,c):
    chat=u.effective_chat.id
    if not is_admin(u.effective_user.id):
        run("INSERT OR IGNORE INTO votes VALUES(?,?,?)",(chat,u.effective_user.id,"skip"))
        n=run("SELECT COUNT(*) n FROM votes WHERE chat=? AND kind='skip'",(chat,)).fetchone()["n"]
        if n<2:return await u.effective_message.reply_text(f"Skip vote: {n}/2")
        run("DELETE FROM votes WHERE chat=? AND kind='skip'",(chat,))
    await advance(c,chat,u.effective_message)
async def advance(c,chat,msg):
    a=run("SELECT * FROM auction WHERE chat=?",(chat,)).fetchone()
    if a:
        if a["bidder"]:
            t=team(chat,a["bidder"])
            if t and t["coins"]>=a["bid"] and len(roster(t["id"]))<5:
                run("UPDATE teams SET coins=coins-? WHERE id=?",(a["bid"],t["id"]))
                run("INSERT OR IGNORE INTO roster VALUES(?,?,?)",(t["id"],a["actress"],a["bid"]))
                await msg.reply_text(f"Winner: {t['name']} for {a['bid']} coins.")
        run("UPDATE actresses SET used=1 WHERE id=?",(a["actress"],))
        run("DELETE FROM auction WHERE chat=?",(chat,))
    nxt=run("SELECT * FROM actresses WHERE used=0 ORDER BY id LIMIT 1").fetchone()
    if nxt:
        run("INSERT OR REPLACE INTO auction VALUES(?,?,?,NULL)",(chat,nxt["id"],max(0,nxt["price"]-1))); await show_auction(c,chat)
    else: await msg.reply_text("Auction list finished.")
async def next_cmd(u,c):
    if not is_admin(u.effective_user.id):return await u.effective_message.reply_text("Admin only.")
    await advance(c,u.effective_chat.id,u.effective_message)
async def endauction(u,c):
    if not is_admin(u.effective_user.id):return await u.effective_message.reply_text("Admin only.")
    run("DELETE FROM auction WHERE chat=?",(u.effective_chat.id,))
    await u.effective_message.reply_text("Auction ended. Qualified 5/5 teams:\n"+("\n".join(x["name"] for x in run("SELECT t.name FROM teams t JOIN roster r ON r.team=t.id WHERE t.chat=? GROUP BY t.id HAVING COUNT(r.actress)=5",(u.effective_chat.id,)).fetchall()) or "No qualified teams yet."))
async def submit(u,c):
    if not u.message.photo:return
    raw=u.message.caption or ""; p=raw.split()
    if len(p)<3 or p[0]!="/submit":return await u.message.reply_text("Caption: /submit Actress Name Category")
    cat=p[-1].lower(); name=" ".join(p[1:-1])
    if cat not in CATEGORIES:return await u.message.reply_text("Categories: "+", ".join(CATEGORIES))
    t=team(u.effective_chat.id,u.effective_user.id)
    if not t:return await u.message.reply_text("Register first.")
    owned=[x["name"].lower() for x in roster(t["id"])]
    if name.lower() not in owned:return await u.message.reply_text("Only actresses in your roster can be submitted.")
    try:run("INSERT INTO submissions(team,category,actress,file) VALUES(?,?,?,?)",(t["id"],cat,name,u.message.photo[-1].file_id))
    except sqlite3.IntegrityError:return await u.message.reply_text("Already submitted in this category.")
    await u.message.reply_text("Photo submission saved.")
async def queue(u,c):
    if not is_admin(u.effective_user.id):return await u.effective_message.reply_text("Admin only.")
    rows=run("SELECT t.name,s.category FROM submissions s JOIN teams t ON t.id=s.team WHERE t.chat=?",(u.effective_chat.id,)).fetchall()
    await u.effective_message.reply_text("📋 Submissions\n"+("\n".join(f"{x['name']}: {x['category']}" for x in rows) or "No submissions."))
async def pollstart(u,c):
    if not is_admin(u.effective_user.id):
        run("INSERT OR IGNORE INTO votes VALUES(?,?,?)",(u.effective_chat.id,u.effective_user.id,"poll"))
        n=run("SELECT COUNT(*) n FROM votes WHERE chat=? AND kind='poll'",(u.effective_chat.id,)).fetchone()["n"]
        if n<2:return await u.effective_message.reply_text(f"Poll launch vote: {n}/2")
    chat=u.effective_chat.id
    if run("SELECT active FROM polls WHERE chat=?",(chat,)).fetchone() and run("SELECT active FROM polls WHERE chat=?",(chat,)).fetchone()["active"]:
        return await u.effective_message.reply_text("A poll is already active. Admin: /endpoll")
    rows=run("SELECT s.*,t.name team FROM submissions s JOIN teams t ON t.id=s.team WHERE t.chat=? ORDER BY s.category,t.name",(chat,)).fetchall()
    if not rows:return await u.effective_message.reply_text("No submissions.")
    run("INSERT INTO polls(chat,active) VALUES(?,1) ON CONFLICT(chat) DO UPDATE SET active=1",(chat,))
    run("DELETE FROM votes WHERE chat=? AND kind='poll'",(chat,))
    for x in rows:
        kb=InlineKeyboardMarkup([[InlineKeyboardButton("❤️ Vote",callback_data=f"vote:{x['id']}")]])
        await c.bot.send_photo(u.effective_chat.id,x["file"],caption=f"{x['team']} · {x['actress']} · {x['category']}",reply_markup=kb)
    await u.effective_message.reply_text("Polls launched!")
async def vote(u,c):
    q=u.callback_query; sid=int(q.data.split(":")[1])
    poll=run("SELECT active FROM polls WHERE chat=?",(q.message.chat_id,)).fetchone()
    submission=run("SELECT s.id FROM submissions s JOIN teams t ON t.id=s.team WHERE s.id=? AND t.chat=?",(sid,q.message.chat_id)).fetchone()
    if not poll or not poll["active"] or not submission:
        return await q.answer("This poll is closed or invalid.",show_alert=True)
    try:
        run("INSERT INTO pollvotes VALUES(?,?)",(sid,q.from_user.id))
        n=run("SELECT COUNT(*) n FROM pollvotes WHERE submission=?",(sid,)).fetchone()["n"]
        await q.answer("Vote counted!")
        await q.edit_message_caption(caption=q.message.caption+f"\nVotes: {n}",reply_markup=q.message.reply_markup)
    except sqlite3.IntegrityError:await q.answer("You already voted.",show_alert=True)
async def endpoll(u,c):
    if not is_admin(u.effective_user.id):return await u.effective_message.reply_text("Admin only.")
    rows=run("SELECT t.name,s.category,COUNT(v.user) votes FROM submissions s JOIN teams t ON t.id=s.team LEFT JOIN pollvotes v ON v.submission=s.id WHERE t.chat=? GROUP BY s.id ORDER BY votes DESC",(u.effective_chat.id,)).fetchall()
    await u.effective_message.reply_text("📊 POLL RESULTS\n"+("\n".join(f"{x['category']}: {x['name']} — {x['votes']} votes" for x in rows) or "No votes."))
async def scoreboard(u,c):
    rows=run("SELECT user,points FROM scores ORDER BY points DESC LIMIT 10").fetchall()
    await u.effective_message.reply_text("🎮 GUESS GAME LEADERBOARD\n"+("\n".join(f"{i}. User {x['user']} — {x['points']} pts" for i,x in enumerate(rows,1)) or "No scores yet."))
def main():
    if not TOKEN: raise RuntimeError("Set BOT_TOKEN in Heroku Config Vars.")
    app=Application.builder().token(TOKEN).build()
    async def set_command_menu(application):
        commands=[
          BotCommand("start","Open Actress Arena menu"),
          BotCommand("addteam","Register a team"),
          BotCommand("myteam","Show your team and roster"),
          BotCommand("teams","List registered teams"),
          BotCommand("leaderboard","Show team leaderboard"),
          BotCommand("list","Show all actresses with clickable image links"),
          BotCommand("actresslist","Show all actresses with clickable image links"),
          BotCommand("guess","Guess the actress"),
          BotCommand("daily","Daily challenge"),
          BotCommand("startauction","Start or vote for auction"),
          BotCommand("skip","Skip or vote to skip auction item"),
          BotCommand("addactress","Admin: add actress"),
          BotCommand("addquestion","Admin: add guess question"),
          BotCommand("next","Admin: next auction item"),
          BotCommand("endauction","Admin: end auction"),
          BotCommand("queue","Admin: view submissions"),
          BotCommand("pollstart","Admin: start poll"),
          BotCommand("endpoll","Admin: end poll and show results"),
          BotCommand("guessleaderboard","Show guess game scores"),
          BotCommand("help","Show all commands")
        ]
        await application.bot.set_my_commands(commands)
    app.post_init=set_command_menu
    for name,fn in [("start",start),("help",start),("addteam",addteam),("myteam",myteam),("teams",teams),("leaderboard",leaderboard),("list",list_actresses),("actresslist",list_actresses),("addactress",addactress),("addquestion",addquestion),("guess",guess),("daily",daily),("startauction",startauction),("skip",skip),("next",next_cmd),("endauction",endauction),("submit",submit),("queue",queue),("pollstart",pollstart),("endpoll",endpoll),("guessleaderboard",scoreboard)]:
        app.add_handler(CommandHandler(name,fn))
    app.add_handler(CallbackQueryHandler(buttons,pattern="^(guess|auction|profile|leader|list|finale|daily|help)$"))
    app.add_handler(CallbackQueryHandler(hint_button,pattern="^hint:"))
    app.add_handler(CallbackQueryHandler(vote,pattern="^vote:"))
    app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r"^/submit"),submit))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_guess))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,bids))
    app.run_polling(drop_pending_updates=True)
if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    main()

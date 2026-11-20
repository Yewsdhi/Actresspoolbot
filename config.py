import os
BOT_TOKEN=os.getenv("BOT_TOKEN","")
ADMIN_IDS={int(x) for x in os.getenv("ADMIN_IDS","").replace(" ","").split(",") if x.isdigit()}
STARTING_COINS=int(os.getenv("STARTING_COINS","300"))
AUCTION_START_VOTES=3
SKIP_VOTES=2
POLL_START_VOTES=2
# Safe, non-sexualized photo themes
CATEGORIES=["traditional","western","redcarpet","casual","cinematic"]

import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {
    int(value) for value in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",")
    if value.isdigit()
}
STARTING_COINS = int(os.getenv("STARTING_COINS", "300"))
AUCTION_START_VOTES = 3
SKIP_VOTES = 2
POLL_START_VOTES = 2
ROSTER_SIZE = 5

# Fashion/editorial themes; no revealing or sexualized categories.
CATEGORIES = ["traditional", "western", "redcarpet", "casual", "cinematic"]

# Bollywood Auction & Poll Bot

Telegram group game bot with team registration, coin bidding, five-actress rosters, finalist photo submissions, and category voting.

## Included features
- `/addteam Team Name` gives 300 coins
- `/myteam`, `/leaderboard`, `/list`
- Admin `/addactress Name, Price, ImageURL`
- `/startauction` requires 3 unique votes (admins start instantly)
- Numeric message bids; `/skip` requires 2 votes
- Admin `/next`, `/team`, `/endauction`
- Photo caption: `/submit Actress Name Category`
- Five safe photo themes: `traditional`, `western`, `redcarpet`, `casual`, `cinematic`
- `/queue`, `/pollstart` (2 votes; admins instant), `/endpoll`

## Heroku deployment
1. Create a Telegram bot with BotFather and copy its token.
2. Deploy this repository to Heroku using the Python buildpack.
3. Set Config Vars:
   - `BOT_TOKEN` = your token
   - `ADMIN_IDS` = your numeric Telegram user ID(s), comma-separated
4. Enable the `worker` dyno.
5. Add a persistent database option before public use. Heroku dyno filesystem is ephemeral; SQLite data may be lost on restart/redeploy. For production, migrate `database.py` to PostgreSQL or mount persistent storage.
6. Add the bot to your group. Give it permission to send photos/messages. Disable privacy mode in BotFather if you want it to read numeric bids sent as ordinary group messages.

## Important
- Only admins can add actresses and force controls.
- Every user may register one team per group.
- A team can win up to five different actresses.
- The bot's photo themes are intentionally non-sexualized fashion/editorial categories.
- Poll voting is one vote per Telegram user per submitted entry.
- Use a trusted source and appropriate rights for actress images.

## Local run
```bash
pip install -r requirements.txt
export BOT_TOKEN="..."
export ADMIN_IDS="123456789"
python bot.py
```

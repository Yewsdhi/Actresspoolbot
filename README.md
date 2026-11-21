# Bollywood Auction & Poll Bot

A Telegram group game bot with team registration, a coin-based actress auction, five-player-roster qualification, and a five-category photo poll finale.

## Player commands

| Command | Description |
|---|---|
| `/start` or `/help` | Show command menu |
| `/addteam Team Name` | Register one team per user in the group; receive 300 coins |
| `/myteam` | View team balance and drafted roster |
| `/leaderboard` | View group rankings |
| `/list` | View actresses still available for auction |
| `/startauction` | Vote to start the auction; 3 unique votes required |
| `/skip` | Vote to skip the current auction item; 2 unique votes required |
| `/actress remove Actress Name` | Remove an actress from the list |
| Send a number | Place a bid during an active auction |
| `/submit Actress Name Category` | Submit a photo with this command in its caption |

## Poll finale categories

Submit one photo for each category using five different actresses from your completed 5/5 team roster:

- `traditional`
- `western`
- `redcarpet`
- `casual`
- `cinematic`

Example photo caption: `/submit Kiara Advani traditional`

A team must have a full five-actress roster to submit. The same drafted actress cannot be used twice by that team. A team can submit only once per category.

`/pollstart` requires 2 unique player votes; admins can launch immediately. Each Telegram user can vote once on each entry. `/queue` shows submission progress and `/endpoll` closes voting and displays results.

## Admin commands

| Command | Description |
|---|---|
| `/addactress Name, Price, ImageURL` | Add an actress to the auction list |
| `/removeactress Actress Name` | Remove an actress from the list |
| `/next` | Force-close the current auction item and move on |
| `/team` | List registered teams |
| `/endauction` | Close the auction and list teams with 5/5 rosters |
| `/queue` | View poll-finale submission status |
| `/pollstart` | Launch the poll immediately |
| `/endpoll` | Close polls and show vote totals |

Admins are identified by Telegram numeric user IDs in `ADMIN_IDS`.

## Heroku deployment

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/Yewsdhi/Actresspoolbot)

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Deploy this repository to Heroku using the Deploy to Heroku button.
3. Set `BOT_TOKEN` to the BotFather token.
4. Set `ADMIN_IDS` to your Telegram numeric user ID (multiple IDs can be comma-separated).
5. Make sure the `worker` process is enabled in Heroku's Resources tab.
6. Add the bot to your Telegram group. For numeric bids, disable BotFather privacy mode so the bot can read ordinary group messages.

### Configuration

- `BOT_TOKEN` — required Telegram bot token.
- `ADMIN_IDS` — required comma-separated Telegram numeric admin IDs.
- `STARTING_COINS` — optional; defaults to `300`.
- `DB_PATH` — optional SQLite file path; defaults to `data/auction.db`.

**Database persistence warning:** this build uses SQLite. Heroku's dyno filesystem is ephemeral, so database contents can be lost when the dyno restarts or is replaced. Do not use this SQLite setup for a production game that needs durable records; use a persistent volume or migrate the database layer to PostgreSQL before relying on long-term scores.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export BOT_TOKEN="YOUR_BOT_TOKEN"
export ADMIN_IDS="123456789"
python bot.py
```

Use images you have permission to share. The built-in poll themes are fashion/editorial categories.

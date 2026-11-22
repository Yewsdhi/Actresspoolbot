# 👑 Actress Arena Gold

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/Yewsdhi/Actresspoolbot)


Telegram bot combining an actress photo-guess game and group auction game. Interface uses inline menu buttons and a premium black-and-gold text style.

## Features
- Inline home menu
- Actress guessing game with hints and points
- Daily challenge entry point
- Guess leaderboard
- Team registration with 300 coins
- Actress catalog and live group auction
- Numeric bids, skip voting, auction close
- Five editorial photo categories for finale submissions
- Inline poll voting and admin results

## Heroku deployment
1. Create a bot with @BotFather and copy the token.
2. Push this project to your own GitHub repository.
3. The `app.json` repository field is set to `https://github.com/Yewsdhi/Actresspoolbot`.
4. Commit and push these ZIP project files into the root of `Yewsdhi/Actresspoolbot`. Then open the Deploy button above.
5. Set Config Vars: `BOT_TOKEN`, `ADMIN_IDS` (comma-separated numeric IDs).
6. Enable the `worker` dyno.

**Database note:** Heroku's local filesystem is ephemeral. `/tmp` is suitable only for testing; for lasting scores, teams, and auctions, migrate SQLite to PostgreSQL before production use.

## Commands
Players: `/start`, `/addteam Team`, `/myteam`, `/leaderboard`, `/list`, `/guess`, `/daily`, `/guessleaderboard`, `/startauction`, `/skip`, `/submit`.
Admins: `/addactress Name, Price, ImageURL`, `/addquestion Answer, Hint, ImageURL`, `/next`, `/endauction`, `/queue`, `/pollstart`, `/endpoll`.

To use guess mode, admin adds question entries with a publicly accessible image URL. Example:
`/addquestion Alia Bhatt, Starred in Gangubai Kathiawadi, https://example.org/alia.jpg`

For auction, add actress records:
`/addactress Alia Bhatt, 100, https://example.org/alia.jpg`

The photo categories are intentionally non-sexualized: `traditional`, `western`, `redcarpet`, `casual`, `cinematic`. Use images you have rights to share.

> The Deploy button points to the GitHub repository. It will only deploy this updated bot after the ZIP contents have been pushed to that repository.

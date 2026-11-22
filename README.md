# 👑 Actress Arena Gold

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/Yewsdhi/Actresspoolbot)


Telegram bot combining an actress photo-guess game and group auction game. Interface uses inline menu buttons and a premium black-and-gold text style.

## Features
- Inline home menu
- Actress guessing game with hints and points
- Daily challenge entry point
- Guess leaderboard
- Team registration with 300 coins, captain/member support, joining/leaving and admin removal
- Team directory and team detail commands
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

**Important database note:** Heroku local files (including `/tmp`) are ephemeral. This build still uses SQLite, so data can reset when the dyno is replaced/restarted. Do not treat it as persistent production storage. A PostgreSQL migration is still required for durable live data.

## Team commands
- `/addteam Royal` — create a team with 300 coins; creator becomes captain.
- `/jointeam Royal` — join an existing team in this group. Each user can belong to one team per group.
- `/leaveteam` — leave as a member (captain cannot leave).
- `/myteam` — show your team and roster.
- `/team Royal` — show a team; `/team` shows your own.
- `/listteams` — list all teams in the current group.
- `/removeteam Royal` — admin-only removal.

## Commands
Players: `/start`, `/addteam Team`, `/jointeam Team`, `/leaveteam`, `/myteam`, `/team [TeamName]`, `/listteams`, `/leaderboard`, `/list` (or `/actresslist`), `/guess`, `/daily`, `/guessleaderboard`, `/startauction`, `/skip`, `/submit`.
Admins: `/addactress Name, Price, ImageURL`, `/addquestion Answer, Hint, ImageURL`, `/removeteam TeamName`, `/next`, `/endauction`, `/queue`, `/pollstart`, `/endpoll`.

To use guess mode, admin adds question entries with a publicly accessible image URL. Example:
`/addquestion Alia Bhatt, Starred in Gangubai Kathiawadi, https://example.org/alia.jpg`

For auction, add actress records:
`/addactress Alia Bhatt, 100, https://example.org/alia.jpg`

The photo categories are intentionally non-sexualized: `traditional`, `western`, `redcarpet`, `casual`, `cinematic`. Use images you have rights to share.

> The Deploy button points to the GitHub repository. It will only deploy this updated bot after the ZIP contents have been pushed to that repository.

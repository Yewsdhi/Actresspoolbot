import os
import sqlite3


class DB:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.c = sqlite3.connect(path, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.init()

    def q(self, sql, args=()):
        cur = self.c.execute(sql, args)
        self.c.commit()
        return cur

    def init(self):
        self.q("""CREATE TABLE IF NOT EXISTS teams(
            id INTEGER PRIMARY KEY, chat INTEGER NOT NULL, owner INTEGER NOT NULL,
            owner_name TEXT NOT NULL, name TEXT NOT NULL, coins INTEGER NOT NULL,
            UNIQUE(chat, owner), UNIQUE(chat, name))""")
        self.q("""CREATE TABLE IF NOT EXISTS actresses(
            id INTEGER PRIMARY KEY, name TEXT UNIQUE, price INTEGER NOT NULL,
            image_url TEXT NOT NULL, used INTEGER DEFAULT 0)""")
        self.q("""CREATE TABLE IF NOT EXISTS auction(
            chat INTEGER PRIMARY KEY, actress INTEGER, current_bid INTEGER, bidder INTEGER)""")
        self.q("""CREATE TABLE IF NOT EXISTS roster(
            id INTEGER PRIMARY KEY, team INTEGER, actress INTEGER, paid INTEGER,
            UNIQUE(team, actress))""")
        self.q("""CREATE TABLE IF NOT EXISTS votes(
            chat INTEGER, user INTEGER, kind TEXT, PRIMARY KEY(chat,user,kind))""")
        self.q("""CREATE TABLE IF NOT EXISTS submissions(
            id INTEGER PRIMARY KEY, team INTEGER, category TEXT, actress_name TEXT,
            file_id TEXT, UNIQUE(team,category))""")
        self.q("""CREATE TABLE IF NOT EXISTS poll_votes(
            submission INTEGER, user INTEGER, PRIMARY KEY(submission,user))""")
        self.q("""CREATE TABLE IF NOT EXISTS poll_state(
            chat INTEGER PRIMARY KEY, active INTEGER DEFAULT 0)""")

    def add_team(self, chat, uid, owner, name, coins):
        try:
            self.q("INSERT INTO teams(chat,owner,owner_name,name,coins) VALUES(?,?,?,?,?)",
                   (chat, uid, owner, name, coins))
            return True, f"Team {name} registered with {coins} coins."
        except sqlite3.IntegrityError:
            return False, "You already have a team or that team name is taken in this group."

    def team(self, chat, uid):
        row = self.q("SELECT * FROM teams WHERE chat=? AND owner=?", (chat, uid)).fetchone()
        return dict(row) if row else None

    def roster(self, team_id):
        rows = self.q("""SELECT a.name,r.paid FROM roster r
                         JOIN actresses a ON a.id=r.actress WHERE r.team=? ORDER BY r.id""",
                      (team_id,)).fetchall()
        return [dict(row) for row in rows]

    def add_actress(self, name, price, image_url):
        try:
            self.q("INSERT INTO actresses(name,price,image_url) VALUES(?,?,?)",
                   (name, price, image_url))
            return True
        except sqlite3.IntegrityError:
            return False

    def actresses(self):
        return [dict(row) for row in self.q("SELECT * FROM actresses ORDER BY name").fetchall()]

    def remove_actress(self, name):
        return self.q("DELETE FROM actresses WHERE lower(name)=lower(?)", (name,)).rowcount > 0

    def next_actress(self):
        row = self.q("SELECT * FROM actresses WHERE used=0 ORDER BY id LIMIT 1").fetchone()
        return dict(row) if row else None

    def begin_auction(self, chat, actress_id, price):
        self.q("INSERT OR REPLACE INTO auction(chat,actress,current_bid,bidder) VALUES(?,?,?,NULL)",
               (chat, actress_id, price - 1))

    def active(self, chat):
        return self.q("SELECT 1 FROM auction WHERE chat=?", (chat,)).fetchone() is not None

    def current(self, chat):
        row = self.q("""SELECT au.*,a.name,a.image_url FROM auction au
                        JOIN actresses a ON a.id=au.actress WHERE au.chat=?""", (chat,)).fetchone()
        return dict(row) if row else None

    def place_bid(self, chat, uid, amount):
        self.q("UPDATE auction SET current_bid=?,bidder=? WHERE chat=?", (amount, uid, chat))

    def finish_current(self, chat):
        item = self.current(chat)
        if not item:
            return None
        result = f"{item['name']} auction closed."
        if item["bidder"] is not None:
            team = self.q("SELECT * FROM teams WHERE chat=? AND owner=?",
                          (chat, item["bidder"])).fetchone()
            if team and team["coins"] >= item["current_bid"]:
                count = self.q("SELECT COUNT(*) n FROM roster WHERE team=?",
                               (team["id"],)).fetchone()["n"]
                if count < 5:
                    self.q("UPDATE teams SET coins=coins-? WHERE id=?",
                           (item["current_bid"], team["id"]))
                    self.q("INSERT OR IGNORE INTO roster(team,actress,paid) VALUES(?,?,?)",
                           (team["id"], item["actress"], item["current_bid"]))
                    result += f" Winner: {team['name']} for {item['current_bid']} coins."
        self.q("UPDATE actresses SET used=1 WHERE id=?", (item["actress"],))
        self.q("DELETE FROM auction WHERE chat=?", (chat,))
        return result

    def clear_auction(self, chat):
        self.q("DELETE FROM auction WHERE chat=?", (chat,))

    def vote(self, chat, uid, kind):
        self.q("INSERT OR IGNORE INTO votes(chat,user,kind) VALUES(?,?,?)", (chat, uid, kind))
        return self.q("SELECT COUNT(*) n FROM votes WHERE chat=? AND kind=?",
                      (chat, kind)).fetchone()["n"]

    def clear_votes(self, chat, kind):
        self.q("DELETE FROM votes WHERE chat=? AND kind=?", (chat, kind))

    def leaderboard(self, chat):
        rows = self.q("""SELECT t.*,COUNT(r.id) count FROM teams t
                         LEFT JOIN roster r ON r.team=t.id WHERE t.chat=?
                         GROUP BY t.id ORDER BY count DESC, t.coins DESC, t.name""",
                      (chat,)).fetchall()
        return [dict(row) for row in rows]

    def qualified(self, chat):
        return [row for row in self.leaderboard(chat) if row["count"] == 5]

    def all_teams(self, chat):
        return [dict(row) for row in self.q(
            "SELECT * FROM teams WHERE chat=? ORDER BY name", (chat,)).fetchall()]

    def actress_used_in_submission(self, team_id, actress_name):
        return self.q("SELECT 1 FROM submissions WHERE team=? AND lower(actress_name)=lower(?)",
                      (team_id, actress_name)).fetchone() is not None

    def submit(self, team_id, category, actress, file_id):
        try:
            self.q("INSERT INTO submissions(team,category,actress_name,file_id) VALUES(?,?,?,?)",
                   (team_id, category, actress, file_id))
            return True, "Photo submission saved."
        except sqlite3.IntegrityError:
            return False, "You have already submitted for this category."

    def submission_status(self, chat):
        output = []
        for team in self.all_teams(chat):
            rows = self.q("SELECT category FROM submissions WHERE team=? ORDER BY category",
                          (team["id"],)).fetchall()
            cats = {row["category"] for row in rows}
            status = " ".join(f"{c}{' ✓' if c in cats else ' ·'}" for c in
                              ("traditional", "western", "redcarpet", "casual", "cinematic"))
            output.append(f"{team['name']} ({len(cats)}/5): {status}")
        return output

    def all_submissions(self, chat):
        rows = self.q("""SELECT s.*,t.name team_name FROM submissions s
                         JOIN teams t ON t.id=s.team WHERE t.chat=?
                         ORDER BY s.category,t.name""", (chat,)).fetchall()
        return [dict(row) for row in rows]

    def set_polls_active(self, chat, active):
        self.q("INSERT OR REPLACE INTO poll_state(chat,active) VALUES(?,?)",
               (chat, int(active)))

    def polls_active(self, chat):
        row = self.q("SELECT active FROM poll_state WHERE chat=?", (chat,)).fetchone()
        return bool(row and row["active"])

    def reset_poll_votes(self, chat):
        self.q("""DELETE FROM poll_votes WHERE submission IN
                  (SELECT s.id FROM submissions s JOIN teams t ON t.id=s.team WHERE t.chat=?)""",
               (chat,))

    def cast_poll_vote(self, chat, uid, submission_id):
        if not self.polls_active(chat):
            return False, 0
        belongs = self.q("""SELECT 1 FROM submissions s JOIN teams t ON t.id=s.team
                            WHERE s.id=? AND t.chat=?""", (submission_id, chat)).fetchone()
        if not belongs:
            return False, 0
        try:
            self.q("INSERT INTO poll_votes(submission,user) VALUES(?,?)",
                   (submission_id, uid))
        except sqlite3.IntegrityError:
            return False, 0
        count = self.q("SELECT COUNT(*) n FROM poll_votes WHERE submission=?",
                       (submission_id,)).fetchone()["n"]
        return True, count

    def submission(self, submission_id):
        row = self.q("""SELECT s.*,t.name team_name FROM submissions s
                        JOIN teams t ON t.id=s.team WHERE s.id=?""",
                     (submission_id,)).fetchone()
        return dict(row) if row else {}

    def poll_results(self, chat):
        rows = self.q("""SELECT s.category,t.name team_name,COUNT(v.user) votes
                         FROM submissions s JOIN teams t ON t.id=s.team
                         LEFT JOIN poll_votes v ON v.submission=s.id
                         WHERE t.chat=? GROUP BY s.id
                         ORDER BY s.category,votes DESC,t.name""", (chat,)).fetchall()
        return [dict(row) for row in rows]

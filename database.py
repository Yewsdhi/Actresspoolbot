import os, sqlite3
class DB:
 def __init__(self,path):
  os.makedirs(os.path.dirname(path) or ".",exist_ok=True); self.c=sqlite3.connect(path,check_same_thread=False); self.c.row_factory=sqlite3.Row; self.init()
 def q(self,sql,args=()): 
  cur=self.c.execute(sql,args); self.c.commit(); return cur
 def init(self):
  self.q("""CREATE TABLE IF NOT EXISTS teams(id INTEGER PRIMARY KEY,chat INTEGER,owner INTEGER,owner_name TEXT,name TEXT,coins INTEGER,UNIQUE(chat,owner),UNIQUE(chat,name))""")
  self.q("""CREATE TABLE IF NOT EXISTS actresses(id INTEGER PRIMARY KEY,name TEXT UNIQUE,price INTEGER,image_url TEXT,used INTEGER DEFAULT 0)""")
  self.q("""CREATE TABLE IF NOT EXISTS auction(chat INTEGER PRIMARY KEY,actress INTEGER,current_bid INTEGER,bidder INTEGER)""")
  self.q("""CREATE TABLE IF NOT EXISTS roster(id INTEGER PRIMARY KEY,team INTEGER,actress INTEGER,paid INTEGER,UNIQUE(team,actress))""")
  self.q("""CREATE TABLE IF NOT EXISTS votes(chat INTEGER,user INTEGER,kind TEXT,PRIMARY KEY(chat,user,kind))""")
  self.q("""CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY,team INTEGER,category TEXT,actress_name TEXT,file_id TEXT,UNIQUE(team,category))""")
  self.q("""CREATE TABLE IF NOT EXISTS poll_votes(submission INTEGER,user INTEGER,PRIMARY KEY(submission,user))""")
  self.q("""CREATE TABLE IF NOT EXISTS poll_state(chat INTEGER PRIMARY KEY,active INTEGER DEFAULT 0)""")
 def add_team(self,chat,uid,owner,name,coins):
  try: self.q("INSERT INTO teams(chat,owner,owner_name,name,coins) VALUES(?,?,?,?,?)",(chat,uid,owner,name,coins)); return True,f"Team {name} registered! {coins} coins added."
  except sqlite3.IntegrityError: return False,"Aapki team pehle se registered hai ya team name taken hai."
 def team(self,chat,uid):
  r=self.q("SELECT * FROM teams WHERE chat=? AND owner=?",(chat,uid)).fetchone(); return dict(r) if r else None
 def roster(self,tid):
  return [dict(x) for x in self.q("SELECT actresses.name,roster.paid FROM roster JOIN actresses ON actresses.id=roster.actress WHERE roster.team=?",(tid,)).fetchall()]
 def add_actress(self,n,p,u): self.q("INSERT OR IGNORE INTO actresses(name,price,image_url) VALUES(?,?,?)",(n,p,u))
 def actresses(self): return [dict(x) for x in self.q("SELECT * FROM actresses ORDER BY name").fetchall()]
 def remove_actress(self,n): return self.q("DELETE FROM actresses WHERE lower(name)=lower(?)",(n,)).rowcount>0
 def next_actress(self): 
  r=self.q("SELECT * FROM actresses WHERE used=0 ORDER BY id LIMIT 1").fetchone()
  return dict(r) if r else None
 def begin_auction(self,chat,aid,price): self.q("INSERT OR REPLACE INTO auction(chat,actress,current_bid,bidder) VALUES(?,?,?,NULL)",(chat,aid,price-1))
 def active(self,chat): return self.q("SELECT 1 FROM auction WHERE chat=?",(chat,)).fetchone() is not None
 def current(self,chat):
  r=self.q("SELECT a.*,x.name,x.image_url FROM auction a JOIN actresses x ON x.id=a.actress WHERE a.chat=?",(chat,)).fetchone(); return dict(r) if r else None
 def place_bid(self,chat,uid,amount): self.q("UPDATE auction SET current_bid=?,bidder=? WHERE chat=?",(amount,uid,chat))
 def finish_current(self,chat):
  a=self.current(chat)
  if not a: return None
  result=f"{a['name']} auction closed."
  if a["bidder"]:
   t=self.q("SELECT * FROM teams WHERE chat=? AND owner=?",(chat,a["bidder"])).fetchone()
   if t and t["coins"]>=a["current_bid"] and self.q("SELECT COUNT(*) n FROM roster WHERE team=?",(t["id"],)).fetchone()["n"]<5:
    self.q("UPDATE teams SET coins=coins-? WHERE id=?",(a["current_bid"],t["id"]))
    self.q("INSERT OR IGNORE INTO roster(team,actress,paid) VALUES(?,?,?)",(t["id"],a["actress"],a["current_bid"]))
    result+=f" Winner: {t['name']} for {a['current_bid']} coins."
  self.q("UPDATE actresses SET used=1 WHERE id=?",(a["actress"],)); self.q("DELETE FROM auction WHERE chat=?",(chat,))
  return result
 def clear_auction(self,chat): self.q("DELETE FROM auction WHERE chat=?",(chat,))
 def vote(self,chat,uid,kind):
  self.q("INSERT OR IGNORE INTO votes(chat,user,kind) VALUES(?,?,?)",(chat,uid,kind))
  return self.q("SELECT COUNT(*) n FROM votes WHERE chat=? AND kind=?",(chat,kind)).fetchone()["n"]
 def leaderboard(self,chat):
  return [dict(x) for x in self.q("SELECT t.*,COUNT(r.id) count FROM teams t LEFT JOIN roster r ON r.team=t.id WHERE t.chat=? GROUP BY t.id ORDER BY count DESC,coins DESC",(chat,)).fetchall()]
 def qualified(self,chat): return [r for r in self.leaderboard(chat) if r["count"]==5]
 def all_teams(self,chat): return [dict(x) for x in self.q("SELECT * FROM teams WHERE chat=? ORDER BY name",(chat,)).fetchall()]
 def submit(self,tid,cat,actress,fileid):
  try: self.q("INSERT INTO submissions(team,category,actress_name,file_id) VALUES(?,?,?,?)",(tid,cat,actress,fileid)); return True,"Submission saved."
  except sqlite3.IntegrityError: return False,"Is category ke liye aapki submission pehle se hai."
 def submission_status(self,chat):
  return [f"{t['name']}: "+", ".join(f"{s['category']} ✓" for s in self.q("SELECT category FROM submissions WHERE team=?",(t["id"],)).fetchall()) for t in self.all_teams(chat)]
 def all_submissions(self,chat):
  return [dict(x) for x in self.q("SELECT s.*,t.name team_name FROM submissions s JOIN teams t ON t.id=s.team WHERE t.chat=? ORDER BY s.category,t.name",(chat,)).fetchall()]
 def set_polls_active(self,chat,active): self.q("INSERT OR REPLACE INTO poll_state(chat,active) VALUES(?,?)",(chat,int(active)))
 def reset_poll_votes(self,chat): self.q("DELETE FROM poll_votes WHERE submission IN (SELECT s.id FROM submissions s JOIN teams t ON t.id=s.team WHERE t.chat=?)",(chat,))
 def cast_poll_vote(self,chat,uid,sid):
  active=self.q("SELECT active FROM poll_state WHERE chat=?",(chat,)).fetchone()
  if not active or not active["active"]: return False,0
  try: self.q("INSERT INTO poll_votes(submission,user) VALUES(?,?)",(sid,uid))
  except sqlite3.IntegrityError: return False,0
  return True,self.q("SELECT COUNT(*) n FROM poll_votes WHERE submission=?",(sid,)).fetchone()["n"]
 def submission(self,sid):
  r=self.q("SELECT s.*,t.name team_name FROM submissions s JOIN teams t ON t.id=s.team WHERE s.id=?",(sid,)).fetchone(); return dict(r) if r else {}
 def poll_results(self,chat):
  return [dict(x) for x in self.q("SELECT s.category,t.name team_name,COUNT(v.user) votes FROM submissions s JOIN teams t ON t.id=s.team LEFT JOIN poll_votes v ON v.submission=s.id WHERE t.chat=? GROUP BY s.id ORDER BY s.category,votes DESC",(chat,)).fetchall()]

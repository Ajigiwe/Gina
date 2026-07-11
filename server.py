from flask import Flask, request, jsonify, send_file
import sqlite3
import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "notes.db")

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

@app.route("/")
def index():
    return HTML

@app.route("/api/notes")
def list_notes():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, content, created_at, updated_at FROM notes ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/notes", methods=["POST"])
def create_note():
    data = request.get_json()
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400
    now = datetime.datetime.now().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO notes (title, content, created_at, updated_at) VALUES (?,?,?,?)",
        (title, content, now, now),
    )
    conn.commit()
    note_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    data = request.get_json()
    conn = get_db()
    existing = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "not found"}), 404
    title = data.get("title", existing["title"]).strip()
    content = data.get("content", existing["content"]).strip()
    now = datetime.datetime.now().isoformat()
    conn.execute(
        "UPDATE notes SET title=?, content=?, updated_at=? WHERE id=?",
        (title, content, now, note_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    conn = get_db()
    existing = conn.execute("SELECT id FROM notes WHERE id=?", (note_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "not found"}), 404
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/backup")
def backup():
    path = os.path.join(BASE_DIR, "backup.sql")
    conn = get_db()
    with open(path, "w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(line + "\n")
    conn.close()
    return send_file(path, as_attachment=True, download_name=f"notes_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")

@app.route("/api/restore", methods=["POST"])
def restore():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    file = request.files["file"]
    conn = get_db()
    conn.execute("DROP TABLE IF EXISTS notes")
    conn.executescript(file.read().decode("utf-8"))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/reset", methods=["POST"])
def reset():
    conn = get_db()
    conn.execute("DROP TABLE IF EXISTS notes")
    conn.commit()
    conn.close()
    get_db()
    return jsonify({"ok": True})

HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>pink notes</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #FFF0F5; --card: #FFFFFF; --accent: #FF69B4; --dark: #FF1493;
    --light: #FFB6C1; --text: #5C0040; --subtle: #C488A0; --save: #FF69B4;
    --radius: 16px;
  }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg);
    color: var(--text); min-height: 100vh; display: flex; justify-content: center;
    padding: 20px; animation: fadeIn 0.6s ease;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes sparkle { 0% { opacity: 1; transform: scale(0) rotate(0deg); } 50% { opacity: 1; transform: scale(1.2) rotate(180deg); } 100% { opacity: 0; transform: scale(0) rotate(360deg); } }
  @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.08); } }
  @keyframes slideIn { from { opacity: 0; transform: translateX(-20px); } to { opacity: 1; transform: translateX(0); } }
  .app { width: 100%; max-width: 540px; display: flex; flex-direction: column; gap: 16px; }
  .header {
    background: linear-gradient(135deg, var(--accent), var(--dark));
    border-radius: var(--radius); padding: 18px 24px; display: flex;
    align-items: center; justify-content: space-between;
    box-shadow: 0 4px 20px rgba(255,105,180,0.25);
  }
  .header h1 { color: #fff; font-size: 1.5rem; font-weight: 700; letter-spacing: 0.5px; }
  .hearts { display: flex; gap: 4px; }
  .hearts span { color: rgba(255,255,255,0.8); font-size: 1.1rem; animation: pulse 2s ease-in-out infinite; }
  .hearts span:nth-child(2) { animation-delay: 0.3s; }
  .hearts span:nth-child(3) { animation-delay: 0.6s; }
  .card {
    background: var(--card); border-radius: var(--radius); padding: 18px 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04); display: flex; flex-direction: column; gap: 10px;
  }
  .card label {
    font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;
    color: var(--subtle); font-weight: 600;
  }
  .card input, .card textarea {
    font-family: inherit; font-size: 0.95rem; padding: 10px 12px;
    border: 1.5px solid var(--light); border-radius: 10px; outline: none;
    background: #FFFAFD; color: var(--text); transition: border-color 0.2s, box-shadow 0.2s;
    resize: vertical;
  }
  .card input:focus, .card textarea:focus {
    border-color: var(--accent); box-shadow: 0 0 0 3px rgba(255,105,180,0.12);
  }
  .card textarea { min-height: 80px; }
  .btn-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn {
    font-family: inherit; font-size: 0.9rem; font-weight: 600; padding: 9px 18px;
    border: none; border-radius: 24px; cursor: pointer; transition: all 0.2s;
    letter-spacing: 0.3px;
  }
  .btn-save { background: var(--save); color: #fff; box-shadow: 0 3px 12px rgba(255,105,180,0.3); }
  .btn-save:hover { background: var(--dark); transform: translateY(-1px); box-shadow: 0 6px 20px rgba(255,20,147,0.35); }
  .btn-save:active { transform: scale(0.96); }
  .btn-reset { background: var(--light); color: #fff; }
  .btn-reset:hover { background: var(--accent); transform: translateY(-1px); }
  .btn-ghost { background: transparent; color: var(--subtle); font-size: 0.8rem; font-weight: 500; padding: 6px 12px; border: 1.5px solid transparent; }
  .btn-ghost:hover { color: var(--accent); border-color: var(--light); }
  .btn-danger {
    background: transparent; color: #E890A0; border: none; font-size: 1.2rem;
    font-weight: 700; width: 28px; height: 28px; display: flex; align-items: center;
    justify-content: center; border-radius: 50%; cursor: pointer; transition: all 0.15s;
    flex-shrink: 0;
  }
  .btn-danger:hover { background: #FFE0E8; color: var(--dark); }
  .list-label {
    font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;
    color: var(--subtle); font-weight: 600; text-align: center; margin-top: 2px;
  }
  .notes-list { display: flex; flex-direction: column; gap: 8px; }
  .empty { text-align: center; color: var(--subtle); font-style: italic; padding: 32px 0; animation: fadeIn 0.5s ease; }
  .note-item {
    background: var(--card); border-radius: 12px; padding: 12px 14px;
    display: flex; align-items: center; gap: 10px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.03); cursor: pointer;
    transition: all 0.2s; animation: slideIn 0.35s ease forwards;
    border-left: 4px solid var(--accent);
  }
  .note-item:hover { transform: translateX(2px); box-shadow: 0 3px 14px rgba(255,105,180,0.12); }
  .note-info { flex: 1; min-width: 0; }
  .note-title { font-weight: 600; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .note-date { font-size: 0.75rem; color: var(--subtle); margin-top: 2px; }
  .sparkle { position: fixed; pointer-events: none; z-index: 999; animation: sparkle 0.7s ease-out forwards; font-size: 1.1rem; }
  .toast {
    position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
    background: var(--text); color: #fff; padding: 10px 24px; border-radius: 20px;
    font-size: 0.85rem; font-weight: 500; opacity: 0; transition: opacity 0.3s;
    z-index: 1000; pointer-events: none;
  }
  .toast.show { opacity: 1; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--light); border-radius: 3px; }
</style>
</head>
<body>
<div class="app">
  <div class="header"><h1>pink notes</h1><div class="hearts"><span>&#9825;</span><span>&#9825;</span><span>&#9825;</span></div></div>
  <div class="card" id="formCard">
    <label>title</label>
    <input type="text" id="titleInput" placeholder="note title..." maxlength="200">
    <label>note</label>
    <textarea id="contentInput" placeholder="write something cute..." rows="3"></textarea>
    <div class="btn-row">
      <button class="btn btn-save" id="saveBtn" onclick="saveNote()">&#10027; save</button>
      <button class="btn btn-reset" onclick="resetDatabase()">&#8634; reset</button>
      <button class="btn btn-ghost" onclick="backup()" style="margin-left:auto;">backup</button>
      <button class="btn btn-ghost" onclick="document.getElementById('restoreFile').click()">restore</button>
      <input type="file" id="restoreFile" accept=".sql" style="display:none" onchange="restore(event)">
    </div>
  </div>
  <div class="list-label">&#8212; &#728;&#728; your notes &#728;&#728; &#8212;</div>
  <div class="notes-list" id="notesList"></div>
</div>
<div class="toast" id="toast"></div>
<script>
  let currentId = null;
  async function loadNotes() {
    const res = await fetch("/api/notes");
    const notes = await res.json();
    const list = document.getElementById("notesList");
    if (!notes.length) {
      list.innerHTML = '<div class="empty">no notes yet &mdash; write your first one!<br><span style="font-size:1.5rem;">&#128150;</span></div>';
      return;
    }
    list.innerHTML = notes.map((n, i) => `
      <div class="note-item" onclick="loadNote(${n.id})" style="animation-delay:${i * 0.04}s">
        <div class="note-info">
          <div class="note-title">${esc(n.title)}</div>
          <div class="note-date">${n.updated_at.substring(0, 16).replace('T', ' ')}</div>
        </div>
        <button class="btn-danger" onclick="event.stopPropagation(); deleteNote(${n.id})">&times;</button>
      </div>
    `).join("");
  }
  async function loadNote(id) {
    const res = await fetch("/api/notes");
    const notes = await res.json();
    const note = notes.find(n => n.id === id);
    if (!note) return;
    currentId = note.id;
    document.getElementById("titleInput").value = note.title;
    document.getElementById("contentInput").value = note.content;
    document.getElementById("titleInput").focus();
  }
  async function resetDatabase() {
    if (!confirm("delete ALL notes forever?")) return;
    const res = await fetch("/api/reset", { method: "POST" });
    if (res.ok) {
      currentId = null;
      document.getElementById("titleInput").value = "";
      document.getElementById("contentInput").value = "";
      await loadNotes();
      toast("all notes deleted ~");
    }
  }
  function newNote() {
    currentId = null;
    document.getElementById("titleInput").value = "";
    document.getElementById("contentInput").value = "";
    document.getElementById("titleInput").focus();
  }
  async function saveNote() {
    const title = document.getElementById("titleInput").value.trim();
    const content = document.getElementById("contentInput").value.trim();
    if (!title) { toast("please give your note a title ~"); return; }
    const method = currentId ? "PUT" : "POST";
    const url = currentId ? `/api/notes/${currentId}` : "/api/notes";
    const res = await fetch(url, {
      method, headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content }),
    });
    if (!res.ok) return toast("something went wrong");
    const note = await res.json();
    currentId = note.id;
    sparkle();
    await loadNotes();
    newNote();
  }
  async function deleteNote(id) {
    if (!confirm("delete this note forever?")) return;
    await fetch(`/api/notes/${id}`, { method: "DELETE" });
    if (currentId === id) newNote();
    await loadNotes();
    toast("note deleted ~");
  }
  async function backup() {
    const res = await fetch("/api/backup");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "notes_backup.sql"; a.click();
    URL.revokeObjectURL(url);
    toast("backup downloaded ~");
  }
  async function restore(e) {
    const file = e.target.files[0];
    if (!file) return;
    if (!confirm("restore will replace all notes. continue?")) { e.target.value = ""; return; }
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/restore", { method: "POST", body: form });
    if (res.ok) { newNote(); await loadNotes(); toast("restored from backup ~"); }
    e.target.value = "";
  }
  function sparkle() {
    const btn = document.getElementById("saveBtn");
    const rect = btn.getBoundingClientRect();
    const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
    const emojis = ["&#10024;", "&#10022;", "&#9825;", "&#10049;", "&#10023;"];
    for (let i = 0; i < 8; i++) {
      const el = document.createElement("div");
      el.className = "sparkle";
      el.innerHTML = emojis[i % emojis.length];
      el.style.left = cx + "px"; el.style.top = cy + "px";
      const angle = (Math.PI * 2 / 8) * i;
      const dist = 40 + Math.random() * 30;
      el.style.animation = "sparkle 0.7s ease-out forwards";
      el.style.animationDelay = (i * 0.04) + "s";
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 800);
    }
  }
  function toast(msg) {
    const t = document.getElementById("toast");
    t.textContent = msg; t.classList.add("show");
    clearTimeout(t._timeout);
    t._timeout = setTimeout(() => t.classList.remove("show"), 2000);
  }
  function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
  document.getElementById("titleInput").addEventListener("keydown", e => {
    if (e.key === "Enter") { e.preventDefault(); document.getElementById("contentInput").focus(); }
  });
  document.getElementById("contentInput").addEventListener("keydown", e => {
    if (e.key === "Enter" && e.ctrlKey) { e.preventDefault(); saveNote(); }
  });
  loadNotes();
</script>
</body>
</html>'''

if __name__ == "__main__":
    import os as _os
    app.run(host="0.0.0.0", port=int(_os.environ.get("PORT", 5050)), debug=False)

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb, os, json
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

def db():
    return MySQLdb.connect(
        host=Config.DB_HOST, user=Config.DB_USER, passwd=Config.DB_PASS,
        db=Config.DB_NAME, charset='utf8mb4'
    )

# Load keyword tags
with open('keyword_tags.json','r',encoding='utf-8') as f:
    KEYWORDS = json.load(f)

def guess_category(text):
    text_l = text.lower()
    best, score = None, 0
    for cat, words in KEYWORDS.items():
        s = sum(1 for w in words if w in text_l)
        if s > score:
            score, best = s, cat
    return best if best else 'General'

# ----------------- Auth -----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        print(f"[DEBUG] Submitted Username: {username}")
        print(f"[DEBUG] Submitted Password: {password}")

        con = db()
        cur = con.cursor()

        cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (username,))
        row = cur.fetchone()

        print(f"[DEBUG] DB Result: {row}")

        if row:
            user_id, db_username, db_hash, role = row
            print(f"[DEBUG] Checking password hash: {check_password_hash(db_hash, password)}")
            if check_password_hash(db_hash, password):
                session['user_id'], session['role'] = user_id, role
                print(f"[DEBUG] Login success. User ID: {user_id}, Role: {role}")
                return redirect(url_for('dashboard'))
            else:
                print("[DEBUG] Password mismatch.")
        else:
            print("[DEBUG] Username not found.")

        flash('Invalid credentials')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

# ----------------- Dashboard -----------------
@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    con = db(); cur = con.cursor()
    cur.execute("SELECT id,title,status,category,created_at FROM tickets ORDER BY id DESC LIMIT 20")
    tickets = cur.fetchall()
    return render_template('dashboard.html', tickets=tickets, role=session.get('role'))

# ----------------- Tickets -----------------
@app.route('/ticket/new', methods=['GET','POST'])
def ticket_new():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']; desc = request.form.get('description','')
        cat = guess_category(title + " " + desc)
        con = db(); cur = con.cursor()
        cur.execute("INSERT INTO tickets (user_id,title,description,category) VALUES (%s,%s,%s,%s)",
                    (session['user_id'], title, desc, cat))
        con.commit()
        return redirect(url_for('dashboard'))
    return render_template('ticket_new.html')

@app.route('/ticket/<int:ticket_id>')
def ticket_view(ticket_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    con = db(); cur = con.cursor()
    cur.execute("SELECT id,title,status,category,description,created_at,assigned_to FROM tickets WHERE id=%s",(ticket_id,))
    ticket = cur.fetchone()
    cur.execute("SELECT c.content, u.username, c.created_at FROM comments c JOIN users u ON c.user_id=u.id WHERE c.ticket_id=%s ORDER BY c.id ASC",(ticket_id,))
    comments = cur.fetchall()
    return render_template('ticket_view.html', ticket=ticket, comments=comments, role=session.get('role'))

# Agent/Admin: assign, status update, comment add
@app.route('/ticket/<int:ticket_id>/update', methods=['POST'])
def ticket_update(ticket_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if session.get('role') not in ('agent','admin'): 
        flash('Only agent/admin'); return redirect(url_for('ticket_view', ticket_id=ticket_id))
    status = request.form.get('status')
    assign = request.form.get('assign_to')
    con = db(); cur = con.cursor()
    if assign:
        cur.execute("UPDATE tickets SET assigned_to=%s WHERE id=%s",(assign, ticket_id))
    if status:
        cur.execute("UPDATE tickets SET status=%s WHERE id=%s",(status, ticket_id))
    con.commit()
    flash('Ticket updated')
    return redirect(url_for('ticket_view', ticket_id=ticket_id))

@app.route('/ticket/<int:ticket_id>/comment', methods=['POST'])
def comment_add(ticket_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    content = request.form.get('content','').strip()
    if content:
        con = db(); cur = con.cursor()
        cur.execute("INSERT INTO comments (ticket_id,user_id,content) VALUES (%s,%s,%s)", (ticket_id, session['user_id'], content))
        con.commit()
    return redirect(url_for('ticket_view', ticket_id=ticket_id))

# ----------------- KB: list, search, CRUD -----------------
@app.route('/kb')
def kb_list():
    q = request.args.get('q','').strip()
    con = db(); cur = con.cursor()
    if q:
        like = f"%{q}%"
        cur.execute("SELECT id,title,category,created_at FROM kb_articles WHERE title LIKE %s OR content LIKE %s ORDER BY id DESC",(like, like))
    else:
        cur.execute("SELECT id,title,category,created_at FROM kb_articles ORDER BY id DESC")
    rows = cur.fetchall()
    return render_template('kb_list.html', articles=rows, q=q)

@app.route('/kb/new', methods=['GET','POST'])
def kb_new():
    if 'user_id' not in session: return redirect(url_for('login'))
    if session.get('role') not in ('agent','admin'): 
        flash('Only agent/admin'); return redirect(url_for('kb_list'))
    if request.method == 'POST':
        title = request.form['title']; content = request.form.get('content',''); category = request.form.get('category','General')
        con = db(); cur = con.cursor()
        cur.execute("INSERT INTO kb_articles (title,content,category) VALUES (%s,%s,%s)", (title, content, category))
        con.commit()
        return redirect(url_for('kb_list'))
    return render_template('kb_new.html')

@app.route('/kb/<int:aid>/edit', methods=['GET','POST'])
def kb_edit(aid):
    if 'user_id' not in session: return redirect(url_for('login'))
    if session.get('role') not in ('agent','admin'): 
        flash('Only agent/admin'); return redirect(url_for('kb_list'))
    con = db(); cur = con.cursor()
    if request.method == 'POST':
        title = request.form['title']; content = request.form.get('content',''); category = request.form.get('category','General')
        cur.execute("UPDATE kb_articles SET title=%s, content=%s, category=%s WHERE id=%s", (title, content, category, aid))
        con.commit(); return redirect(url_for('kb_list'))
    cur.execute("SELECT id,title,content,category FROM kb_articles WHERE id=%s",(aid,))
    art = cur.fetchone()
    return render_template('kb_edit.html', art=art)

# ----------------- Reports -----------------
@app.route('/reports')
def reports():
    if 'user_id' not in session: return redirect(url_for('login'))
    con = db(); cur = con.cursor()
    cur.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
    by_status = cur.fetchall()
    cur.execute("SELECT category, COUNT(*) FROM tickets GROUP BY category")
    by_category = cur.fetchall()
    return render_template('reports.html', by_status=by_status, by_category=by_category)

# ----------------- Users (for assigning) -----------------
@app.route('/users/agents')
def users_agents():
    if 'user_id' not in session: return ""
    con = db(); cur = con.cursor()
    cur.execute("SELECT id,username FROM users WHERE role IN ('agent','admin') ORDER BY username ASC")
    return dict(cur.fetchall())  # quick JSON-like, not used directly in templates

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, json
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def db():
    con = sqlite3.connect(Config.DATABASE_URL)
    con.row_factory = sqlite3.Row
    return con

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
# ----------------- Auth -----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        con = db()
        cur = con.cursor()
        cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row and check_password_hash(row['password_hash'], password):
            session['user_id'], session['role'] = row['id'], row['role']
            return redirect(url_for('dashboard'))
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
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    category = request.args.get('category', '').strip()
    con = db()
    cur = con.cursor()
    sql = "SELECT id, title, status, category, priority, created_at FROM tickets"
    conditions, params = [], []
    if q:
        conditions.append("title LIKE ?")
        params.append(f"%{q}%")
    if status:
        conditions.append("status = ?")
        params.append(status)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id DESC LIMIT 100"
    cur.execute(sql, tuple(params))
    tickets = cur.fetchall()
    cur.execute("SELECT DISTINCT category FROM tickets WHERE category IS NOT NULL ORDER BY category")
    categories = [row[0] for row in cur.fetchall()]
    return render_template('dashboard.html', tickets=tickets, role=session.get('role'),
                           categories=categories, current_filters={'q': q, 'status': status, 'category': category})

# ----------------- Tickets -----------------
@app.route('/ticket/new', methods=['GET','POST'])
def ticket_new():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        desc = request.form.get('description','')
        priority = request.form.get('priority', 'Medium')
        cat = guess_category(title + " " + desc)
        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO tickets (user_id,title,description,category,priority) VALUES (?,?,?,?,?)",
                    (session['user_id'], title, desc, cat, priority))
        new_ticket_id = cur.lastrowid
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename != '':
                original_filename = secure_filename(file.filename)
                stored_filename = f"{new_ticket_id}_{original_filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], stored_filename))
                cur.execute("INSERT INTO attachments (ticket_id, original_filename, stored_filename) VALUES (?,?,?)",
                            (new_ticket_id, original_filename, stored_filename))
        con.commit()
        return redirect(url_for('ticket_view', ticket_id=new_ticket_id))
    return render_template('ticket_new.html')

@app.route('/ticket/<int:ticket_id>')
def ticket_view(ticket_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    con = db()
    cur = con.cursor()
    cur.execute("SELECT id,title,status,category,priority,description,created_at,assigned_to FROM tickets WHERE id=?",(ticket_id,))
    ticket = cur.fetchone()
    cur.execute("SELECT c.content, u.username, c.created_at FROM comments c JOIN users u ON c.user_id=u.id WHERE c.ticket_id=? ORDER BY c.id ASC",(ticket_id,))
    comments = cur.fetchall()
    cur.execute("SELECT id, original_filename, stored_filename FROM attachments WHERE ticket_id=?", (ticket_id,))
    attachments = cur.fetchall()
    return render_template('ticket_view.html', ticket=ticket, comments=comments, attachments=attachments, role=session.get('role'))

@app.route('/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Agent/Admin: assign, status update, comment add
@app.route('/ticket/<int:ticket_id>/update', methods=['POST'])
def ticket_update(ticket_id):
    if session.get('role') not in ('agent','admin'): 
        flash('Only agent/admin'); return redirect(url_for('ticket_view', ticket_id=ticket_id))
    status = request.form.get('status')
    priority = request.form.get('priority')
    assign = request.form.get('assign_to')
    con = db(); cur = con.cursor()
    if assign:
        cur.execute("UPDATE tickets SET assigned_to=? WHERE id=?",(assign, ticket_id))
    if status:
        cur.execute("UPDATE tickets SET status=? WHERE id=?",(status, ticket_id))
    if priority:
        cur.execute("UPDATE tickets SET priority=? WHERE id=?",(priority, ticket_id))
    con.commit()
    flash('Ticket updated')
    return redirect(url_for('ticket_view', ticket_id=ticket_id))

@app.route('/ticket/<int:ticket_id>/comment', methods=['POST'])
def comment_add(ticket_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    content = request.form.get('content','').strip()
    if content:
        con = db(); cur = con.cursor()
        cur.execute("INSERT INTO comments (ticket_id,user_id,content) VALUES (?,?,?)", (ticket_id, session['user_id'], content))
        con.commit()
    return redirect(url_for('ticket_view', ticket_id=ticket_id))

# ----------------- KB: list, search, CRUD -----------------
@app.route('/kb')
def kb():
    q = request.args.get('q','').strip()
    con = db(); cur = con.cursor()
    if q:
        like = f"%{q}%"
        cur.execute("SELECT id,title,category,created_at FROM kb_articles WHERE title LIKE ? OR content LIKE ? ORDER BY id DESC",(like, like))
    else:
        cur.execute("SELECT id,title,category,created_at FROM kb_articles ORDER BY id DESC")
    rows = cur.fetchall()
    return render_template('kb_list.html', articles=rows, q=q)

@app.route('/kb/new', methods=['GET','POST'])
def kb_new():
    if session.get('role') not in ('agent','admin'): 
        flash('Only agent/admin'); return redirect(url_for('kb'))
    if request.method == 'POST':
        title = request.form['title']; content = request.form.get('content',''); category = request.form.get('category','General')
        con = db(); cur = con.cursor()
        cur.execute("INSERT INTO kb_articles (title,content,category) VALUES (?,?,?)", (title, content, category))
        con.commit()
        return redirect(url_for('kb'))
    return render_template('kb_new.html')

@app.route('/kb/<int:aid>/edit', methods=['GET','POST'])
def kb_edit(aid):
    if session.get('role') not in ('agent','admin'): 
        flash('Only agent/admin'); return redirect(url_for('kb'))
    con = db(); cur = con.cursor()
    if request.method == 'POST':
        title = request.form['title']; content = request.form.get('content',''); category = request.form.get('category','General')
        cur.execute("UPDATE kb_articles SET title=?, content=?, category=? WHERE id=?", (title, content, category, aid))
        con.commit(); return redirect(url_for('kb'))
    cur.execute("SELECT id,title,content,category FROM kb_articles WHERE id=?",(aid,))
    art = cur.fetchone()
    return render_template('kb_edit.html', art=art)

# ----------------- Reports -----------------
@app.route('/reports')
def reports():
    if 'user_id' not in session: return redirect(url_for('login'))
    con = db()
    cur = con.cursor()

    cur.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
    by_status = cur.fetchall()

    cur.execute("SELECT category, COUNT(*) as count FROM tickets GROUP BY category")
    by_category = cur.fetchall()

    # Calculate metrics for the top cards
    metrics = {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}
    for row in by_status:
        status = row['status']
        count = row['count']
        if status in metrics:
            metrics[status] = count
        metrics['total'] += count

    # Prepare data for ECharts
    status_chart_data = [{'value': row['count'], 'name': row['status']} for row in by_status]
    category_chart_labels = [row['category'] for row in by_category]
    category_chart_values = [row['count'] for row in by_category]

    return render_template('reports.html',
                           by_status=by_status,
                           by_category=by_category,
                           metrics=metrics,
                           status_chart_data=json.dumps(status_chart_data),
                           category_chart_labels=json.dumps(category_chart_labels),
                           category_chart_values=json.dumps(category_chart_values))

# ----------------- User Management -----------------
@app.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    if session.get('role') != 'admin':
        flash('Admin access required.')
        return redirect(url_for('dashboard'))

    con = db()
    cur = con.cursor()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('role')
        if user_id and new_role:
            # Prevent admin from demoting themselves if they are the only admin
            if int(user_id) == session.get('user_id') and new_role != 'admin':
                cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
                admin_count = cur.fetchone()['count']
                if admin_count <= 1:
                    flash('Cannot demote the only admin.')
                    return redirect(url_for('manage_users'))
            
            cur.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
            con.commit()
            flash(f"User role updated.")
        return redirect(url_for('manage_users'))

    cur.execute("SELECT id, username, role FROM users ORDER BY id")
    users = cur.fetchall()
    return render_template('user_management.html', users=users)


@app.route('/users/agents')
def users_agents():
    if 'user_id' not in session: return ""
    con = db(); cur = con.cursor()
    cur.execute("SELECT id,username FROM users WHERE role IN ('agent','admin') ORDER BY username ASC")
    return dict(cur.fetchall())  # quick JSON-like, not used directly in templates

if __name__ == '__main__':
    app.run(debug=True)
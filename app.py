from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, Response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, json, csv, io
from datetime import datetime, timezone
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def db():
    con = sqlite3.connect(Config.DATABASE_URL)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

with open('keyword_tags.json', 'r', encoding='utf-8') as f:
    KEYWORDS = json.load(f)

def guess_category(text):
    text_l = text.lower()
    best, score = None, 0
    for cat, words in KEYWORDS.items():
        s = sum(1 for w in words if w in text_l)
        if s > score:
            score, best = s, cat
    return best if best else 'General'

# -------------------- Jinja Filters --------------------
@app.template_filter('timeago')
def timeago_filter(dt_str):
    """Convert a datetime string to a relative 'time ago' string."""
    if not dt_str:
        return ''
    try:
        dt = datetime.strptime(str(dt_str)[:19], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return str(dt_str)
    now = datetime.now()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return 'just now'
    minutes = seconds // 60
    if minutes < 60:
        return f'{minutes}m ago'
    hours = minutes // 60
    if hours < 24:
        return f'{hours}h ago'
    days = hours // 24
    if days < 7:
        return f'{days}d ago'
    if days < 30:
        weeks = days // 7
        return f'{weeks}w ago'
    if days < 365:
        months = days // 30
        return f'{months}mo ago'
    years = days // 365
    return f'{years}y ago'

# -------------------- Context Processor --------------------
@app.context_processor
def inject_notifications():
    """Make unread notification count available in all templates."""
    if 'user_id' in session:
        con = db()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) as c FROM notifications WHERE user_id = ? AND is_read = 0", (session['user_id'],))
        count = cur.fetchone()['c']
        return {'unread_count': count}
    return {'unread_count': 0}

def notify(user_id, ticket_id, message):
    """Create a notification for a user."""
    con = db()
    cur = con.cursor()
    cur.execute("INSERT INTO notifications (user_id, ticket_id, message) VALUES (?, ?, ?)",
                (user_id, ticket_id, message))
    con.commit()

def log_activity(ticket_id, user_id, action, detail=None):
    """Log an activity on a ticket."""
    con = db()
    cur = con.cursor()
    cur.execute("INSERT INTO activity_log (ticket_id, user_id, action, detail) VALUES (?, ?, ?, ?)",
                (ticket_id, user_id, action, detail))
    con.commit()

# -------------------- Error Handlers --------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# -------------------- Landing --------------------
@app.route('/')
def landing():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    con = db()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) as c FROM tickets WHERE status = 'closed'")
    total_tickets = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM users")
    total_users = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM kb_articles")
    kb_articles = cur.fetchone()['c']
    return render_template('landing.html', landing_stats={
        'total_tickets': total_tickets,
        'total_users': total_users,
        'kb_articles': kb_articles,
    })

# -------------------- Auth --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        con = db()
        cur = con.cursor()
        cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row and check_password_hash(row['password_hash'], password):
            session['user_id'] = row['id']
            session['username'] = row['username']
            session['role'] = row['role']
            flash('Welcome back, {}!'.format(row['username']), 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        if len(password) < 4:
            flash('Password must be at least 4 characters.', 'error')
            return render_template('register.html')
        con = db()
        cur = con.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            flash('Username already taken.', 'error')
            return render_template('register.html')
        cur.execute("INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, 'student')",
                    (username, email or None, generate_password_hash(password)))
        con.commit()
        flash('Account created! Please sign in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

# -------------------- Dashboard --------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    category = request.args.get('category', '').strip()
    con = db()
    cur = con.cursor()

    sql = "SELECT id, title, status, category, priority, created_at FROM tickets"
    conditions, params = [], []
    if session.get('role') == 'student':
        conditions.append("user_id = ?")
        params.append(session['user_id'])
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

    stats = {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}
    cur.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
    for row in cur.fetchall():
        s = row['status']
        if s in stats:
            stats[s] = row['count']
        stats['total'] += row['count']

    return render_template('dashboard.html', tickets=tickets, role=session.get('role'),
                           categories=categories, stats=stats,
                           current_filters={'q': q, 'status': status, 'category': category})

# -------------------- Tickets --------------------
@app.route('/ticket/new', methods=['GET', 'POST'])
def ticket_new():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        desc = request.form.get('description', '')
        priority = request.form.get('priority', 'Medium')
        cat = guess_category(title + " " + desc)
        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO tickets (user_id, title, description, category, priority) VALUES (?, ?, ?, ?, ?)",
                    (session['user_id'], title, desc, cat, priority))
        new_ticket_id = cur.lastrowid
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename != '':
                original_filename = secure_filename(file.filename)
                stored_filename = f"{new_ticket_id}_{original_filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], stored_filename))
                cur.execute("INSERT INTO attachments (ticket_id, original_filename, stored_filename) VALUES (?, ?, ?)",
                            (new_ticket_id, original_filename, stored_filename))
        con.commit()
        log_activity(new_ticket_id, session['user_id'], 'created', f'Ticket created with priority {priority}')
        flash('Ticket created successfully!', 'success')
        return redirect(url_for('ticket_view', ticket_id=new_ticket_id))
    return render_template('ticket_new.html')

@app.route('/ticket/<int:ticket_id>')
def ticket_view(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    con = db()
    cur = con.cursor()
    cur.execute("SELECT id, title, status, category, priority, description, created_at, assigned_to, user_id FROM tickets WHERE id = ?", (ticket_id,))
    ticket = cur.fetchone()
    if not ticket:
        flash('Ticket not found.', 'error')
        return redirect(url_for('dashboard'))
    cur.execute("SELECT c.content, u.username, c.created_at FROM comments c JOIN users u ON c.user_id = u.id WHERE c.ticket_id = ? ORDER BY c.id ASC", (ticket_id,))
    comments = cur.fetchall()
    cur.execute("SELECT id, original_filename, stored_filename FROM attachments WHERE ticket_id = ?", (ticket_id,))
    attachments = cur.fetchall()
    cur.execute("SELECT a.action, a.detail, a.created_at, u.username FROM activity_log a JOIN users u ON a.user_id = u.id WHERE a.ticket_id = ? ORDER BY a.id ASC", (ticket_id,))
    activities = cur.fetchall()
    # Mark notifications as read for this ticket
    cur.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ? AND ticket_id = ?", (session['user_id'], ticket_id))
    con.commit()
    return render_template('ticket_view.html', ticket=ticket, comments=comments, attachments=attachments, activities=activities, role=session.get('role'))

@app.route('/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/ticket/<int:ticket_id>/update', methods=['POST'])
def ticket_update(ticket_id):
    if session.get('role') not in ('agent', 'admin'):
        flash('Only agents and admins can update tickets.', 'error')
        return redirect(url_for('ticket_view', ticket_id=ticket_id))
    status = request.form.get('status')
    priority = request.form.get('priority')
    assign = request.form.get('assign_to')
    con = db()
    cur = con.cursor()
    # Get ticket owner for notification
    cur.execute("SELECT user_id, status as old_status FROM tickets WHERE id = ?", (ticket_id,))
    ticket_row = cur.fetchone()
    ticket_owner = ticket_row['user_id'] if ticket_row else None

    if assign:
        cur.execute("UPDATE tickets SET assigned_to = ? WHERE id = ?", (assign, ticket_id))
        log_activity(ticket_id, session['user_id'], 'assigned', f'Assigned to user #{assign}')
        if ticket_owner and ticket_owner != session['user_id']:
            notify(ticket_owner, ticket_id, f'Your ticket #{ticket_id} has been assigned to an agent.')
    if status:
        cur.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        log_activity(ticket_id, session['user_id'], 'status_change', f'Status changed to {status}')
        if ticket_owner and ticket_owner != session['user_id']:
            status_label = status.replace('_', ' ').title()
            notify(ticket_owner, ticket_id, f'Your ticket #{ticket_id} status changed to {status_label}.')
    if priority:
        cur.execute("UPDATE tickets SET priority = ? WHERE id = ?", (priority, ticket_id))
        log_activity(ticket_id, session['user_id'], 'priority_change', f'Priority changed to {priority}')
    con.commit()
    flash('Ticket updated successfully.', 'success')
    return redirect(url_for('ticket_view', ticket_id=ticket_id))

@app.route('/ticket/<int:ticket_id>/comment', methods=['POST'])
def comment_add(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    content = request.form.get('content', '').strip()
    if content:
        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO comments (ticket_id, user_id, content) VALUES (?, ?, ?)", (ticket_id, session['user_id'], content))
        log_activity(ticket_id, session['user_id'], 'comment', 'Added a comment')
        # Notify ticket owner if commenter is not the owner
        cur.execute("SELECT user_id FROM tickets WHERE id = ?", (ticket_id,))
        row = cur.fetchone()
        if row and row['user_id'] != session['user_id']:
            notify(row['user_id'], ticket_id, f'{session.get("username", "Someone")} commented on ticket #{ticket_id}.')
        con.commit()
        flash('Comment added.', 'success')
    return redirect(url_for('ticket_view', ticket_id=ticket_id))

# -------------------- Notifications --------------------
@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    con = db()
    cur = con.cursor()
    cur.execute("SELECT id, ticket_id, message, is_read, created_at FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 50", (session['user_id'],))
    notifs = cur.fetchall()
    return render_template('notifications.html', notifications=notifs)

@app.route('/notifications/read', methods=['POST'])
def mark_all_read():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    con = db()
    cur = con.cursor()
    cur.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (session['user_id'],))
    con.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))

# -------------------- Knowledge Base --------------------
@app.route('/kb')
def kb():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    q = request.args.get('q', '').strip()
    con = db()
    cur = con.cursor()
    if q:
        like = f"%{q}%"
        cur.execute("SELECT id, title, category, created_at FROM kb_articles WHERE title LIKE ? OR content LIKE ? ORDER BY id DESC", (like, like))
    else:
        cur.execute("SELECT id, title, category, created_at FROM kb_articles ORDER BY id DESC")
    rows = cur.fetchall()
    return render_template('kb_list.html', articles=rows, q=q)

@app.route('/kb/new', methods=['GET', 'POST'])
def kb_new():
    if session.get('role') not in ('agent', 'admin'):
        flash('Only agents and admins can create articles.', 'error')
        return redirect(url_for('kb'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form.get('content', '')
        category = request.form.get('category', 'General')
        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO kb_articles (title, content, category) VALUES (?, ?, ?)", (title, content, category))
        con.commit()
        flash('Article created!', 'success')
        return redirect(url_for('kb'))
    return render_template('kb_new.html')

@app.route('/kb/<int:aid>/edit', methods=['GET', 'POST'])
def kb_edit(aid):
    if session.get('role') not in ('agent', 'admin'):
        flash('Only agents and admins can edit articles.', 'error')
        return redirect(url_for('kb'))
    con = db()
    cur = con.cursor()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form.get('content', '')
        category = request.form.get('category', 'General')
        cur.execute("UPDATE kb_articles SET title = ?, content = ?, category = ? WHERE id = ?", (title, content, category, aid))
        con.commit()
        flash('Article updated!', 'success')
        return redirect(url_for('kb'))
    cur.execute("SELECT id, title, content, category FROM kb_articles WHERE id = ?", (aid,))
    art = cur.fetchone()
    if not art:
        flash('Article not found.', 'error')
        return redirect(url_for('kb'))
    return render_template('kb_edit.html', art=art)

# -------------------- Reports --------------------
@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    con = db()
    cur = con.cursor()

    cur.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
    by_status = cur.fetchall()

    cur.execute("SELECT category, COUNT(*) as count FROM tickets GROUP BY category")
    by_category = cur.fetchall()

    metrics = {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}
    for row in by_status:
        s = row['status']
        c = row['count']
        if s in metrics:
            metrics[s] = c
        metrics['total'] += c

    status_chart_data = [{'value': row['count'], 'name': row['status']} for row in by_status]
    category_chart_labels = [row['category'] for row in by_category]
    category_chart_values = [row['count'] for row in by_category]

    return render_template('reports.html',
                           by_status=by_status, by_category=by_category, metrics=metrics,
                           status_chart_data=json.dumps(status_chart_data),
                           category_chart_labels=json.dumps(category_chart_labels),
                           category_chart_values=json.dumps(category_chart_values))

@app.route('/reports/export')
def export_csv():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    con = db()
    cur = con.cursor()
    cur.execute("SELECT t.id, t.title, t.status, t.priority, t.category, t.created_at, u.username as submitter FROM tickets t JOIN users u ON t.user_id = u.id ORDER BY t.id DESC")
    rows = cur.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Ticket ID', 'Title', 'Status', 'Priority', 'Category', 'Created At', 'Submitted By'])
    for r in rows:
        writer.writerow([r['id'], r['title'], r['status'], r['priority'], r['category'], r['created_at'], r['submitter']])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=tickets_report.csv'}
    )

# -------------------- User Management --------------------
@app.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    if session.get('role') != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('dashboard'))

    con = db()
    cur = con.cursor()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('role')
        if user_id and new_role:
            if int(user_id) == session.get('user_id') and new_role != 'admin':
                cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
                admin_count = cur.fetchone()['count']
                if admin_count <= 1:
                    flash('Cannot demote the only admin.', 'warning')
                    return redirect(url_for('manage_users'))
            cur.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
            con.commit()
            flash('User role updated.', 'success')
        return redirect(url_for('manage_users'))

    cur.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id")
    users = cur.fetchall()
    return render_template('user_management.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)

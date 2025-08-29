import os, MySQLdb
from werkzeug.security import generate_password_hash

def db():
    return MySQLdb.connect(
        host=os.getenv('DB_HOST','127.0.0.1'),
        user=os.getenv('DB_USER','root'),
        passwd=os.getenv('DB_PASS','Rihan@#$%80'),
        db=os.getenv('DB_NAME','campus'),
        charset='utf8mb4'
    )

con = db(); cur = con.cursor()
cur.execute("INSERT IGNORE INTO users (username,password_hash,role) VALUES (%s,%s,%s)", ("student1", generate_password_hash("pass123"), "student"))
cur.execute("INSERT IGNORE INTO users (username,password_hash,role) VALUES (%s,%s,%s)", ("agent1", generate_password_hash("pass123"), "agent"))
cur.execute("INSERT IGNORE INTO users (username,password_hash,role) VALUES (%s,%s,%s)", ("admin1", generate_password_hash("pass123"), "admin"))

# sample KB
cur.execute("INSERT IGNORE INTO kb_articles (id,title,content,category) VALUES (1,'Reset Wi-Fi Password','Steps to reset campus Wi-Fi password...','IT Support')")
cur.execute("INSERT IGNORE INTO kb_articles (id,title,content,category) VALUES (2,'Fee Payment Portal','How to pay fees online...','Accounts')")
con.commit()
print("Seeded users (student1/agent1/admin1, pass: pass123) and KB articles.")
"""
Seed the database with demo data for presentation.
Run: python seed_data.py
"""
import sqlite3, os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'campus_helpdesk.db')

def seed():
    # Delete old DB if exists for clean re-seed
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed old database.")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    with open('schema.sql', 'r') as f:
        cur.executescript(f.read())

    # --- Users (with emails) ---
    users = [
        ('admin', 'admin@campus.edu', generate_password_hash('admin123'), 'admin'),
        ('agent_priya', 'priya.sharma@campus.edu', generate_password_hash('agent123'), 'agent'),
        ('agent_rahul', 'rahul.verma@campus.edu', generate_password_hash('agent123'), 'agent'),
        ('student_aarav', 'aarav.patel@student.campus.edu', generate_password_hash('student123'), 'student'),
        ('student_neha', 'neha.gupta@student.campus.edu', generate_password_hash('student123'), 'student'),
        ('student_kabir', 'kabir.singh@student.campus.edu', generate_password_hash('student123'), 'student'),
        ('student_ananya', 'ananya.reddy@student.campus.edu', generate_password_hash('student123'), 'student'),
        ('student_rohan', 'rohan.joshi@student.campus.edu', generate_password_hash('student123'), 'student'),
    ]
    cur.executemany("INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)", users)

    # --- Tickets ---
    tickets = [
        (4, 'Wi-Fi not working in Library Block B', 'I have been unable to connect to the campus Wi-Fi in Library Block B since yesterday. My laptop and phone both show the network but cannot authenticate. Other students are also facing the same issue.', 'IT Support', 'High', 'open', 2),
        (5, 'Request for grade correction in Mathematics', 'My marks for the mid-semester Mathematics exam seem incorrect. I scored 78 on paper but the portal shows 68. I have the answer sheet copy for reference.', 'Academics', 'High', 'in_progress', 2),
        (6, 'Fee receipt not generated after payment', 'I paid the semester fee through the online portal 3 days ago. The amount has been debited but the receipt has not been generated. Transaction ID: TXN20260315001.', 'Accounts', 'Medium', 'open', None),
        (4, 'Hostel room water leakage', 'There is a water leakage from the ceiling of Room 304 in Boys Hostel A. It has been getting worse and is damaging my books and electronics.', 'Hostel', 'High', 'in_progress', 3),
        (7, 'Unable to access exam schedule on portal', 'The exam schedule page shows a 404 error when I click on "View Schedule" in the student portal. I need to check my end-semester exam dates urgently.', 'IT Support', 'Medium', 'open', None),
        (5, 'Scholarship application status pending', 'I submitted my merit scholarship application 2 months ago but the status still shows "Under Review". The deadline for disbursement is next week.', 'Accounts', 'High', 'open', 3),
        (8, 'Mess food quality complaint', 'The quality of food in the hostel mess has deteriorated significantly. Multiple students have reported stomach issues. The breakfast served today was stale.', 'Hostel', 'Medium', 'closed', 3),
        (6, 'Printer not working in Computer Lab 2', 'The printer in Computer Lab 2 has been showing "out of toner" error for 5 days. I have an assignment submission tomorrow.', 'IT Support', 'Medium', 'open', None),
        (4, 'Course enrollment issue for elective', 'I am unable to enroll in "Machine Learning" elective for next semester. The system shows the course as full, but my advisor said seats are available.', 'Academics', 'Low', 'closed', 2),
        (7, 'Request for hostel room change', 'I would like a room change from Room 102 to any room on the 3rd floor of Girls Hostel B. My current room has poor ventilation.', 'Hostel', 'Low', 'in_progress', 3),
        (8, 'Email account locked after password reset', 'I tried to reset my campus email password and now the account is completely locked. I need access for a project submission due tomorrow.', 'IT Support', 'High', 'open', 2),
        (5, 'Attendance discrepancy in Physics class', 'The portal shows I have 65% attendance in Physics, but I have attended all classes. I have signed the register every day.', 'Academics', 'Medium', 'open', None),
    ]
    cur.executemany(
        "INSERT INTO tickets (user_id, title, description, category, priority, status, assigned_to) VALUES (?, ?, ?, ?, ?, ?, ?)",
        tickets
    )

    # --- Comments ---
    comments = [
        (1, 2, 'We have notified the IT infrastructure team. They will inspect the router in Block B today.'),
        (1, 3, 'We are checking with the network team. Can you share your student ID for verification?'),
        (2, 2, 'The issue has been identified as a faulty router. Replacement is scheduled for tomorrow morning.'),
        (2, 4, 'Thank you for reporting. I have forwarded this to the Mathematics department HOD.'),
        (4, 3, 'Maintenance team has been notified. They will visit your room by evening today.'),
        (4, 2, 'Thank you for your patience. The plumber visited and identified the source of the leak.'),
        (7, 3, 'The mess committee has taken note. We have changed the food vendor starting this week.'),
        (7, 3, 'Closing this ticket as the issue has been resolved. Please reopen if the problem persists.'),
        (9, 2, 'Your enrollment has been processed manually. Please check the portal now.'),
        (9, 2, 'Glad to help! Closing this ticket. Feel free to reach out if you need anything else.'),
    ]
    cur.executemany("INSERT INTO comments (ticket_id, user_id, content) VALUES (?, ?, ?)", comments)

    # --- Activity Log ---
    activities = [
        (1, 4, 'created', 'Ticket created with priority High'),
        (1, 2, 'assigned', 'Assigned to agent_priya'),
        (1, 2, 'comment', 'Added a comment'),
        (2, 5, 'created', 'Ticket created with priority High'),
        (2, 2, 'status_change', 'Status changed to in_progress'),
        (2, 2, 'comment', 'Added a comment'),
        (4, 4, 'created', 'Ticket created with priority High'),
        (4, 3, 'assigned', 'Assigned to agent_rahul'),
        (4, 3, 'status_change', 'Status changed to in_progress'),
        (7, 8, 'created', 'Ticket created with priority Medium'),
        (7, 3, 'status_change', 'Status changed to closed'),
        (9, 4, 'created', 'Ticket created with priority Low'),
        (9, 2, 'status_change', 'Status changed to closed'),
    ]
    cur.executemany("INSERT INTO activity_log (ticket_id, user_id, action, detail) VALUES (?, ?, ?, ?)", activities)

    # --- Notifications ---
    notifications = [
        (4, 1, 'Your ticket #1 has been assigned to an agent.', 1),
        (4, 1, 'agent_priya commented on ticket #1.', 0),
        (5, 2, 'Your ticket #2 status changed to In Progress.', 1),
        (5, 2, 'agent_priya commented on ticket #2.', 0),
        (4, 4, 'Your ticket #4 has been assigned to an agent.', 0),
        (4, 4, 'agent_rahul commented on ticket #4.', 0),
        (8, 7, 'Your ticket #7 status changed to Closed.', 1),
        (4, 9, 'Your ticket #9 status changed to Closed.', 1),
    ]
    cur.executemany("INSERT INTO notifications (user_id, ticket_id, message, is_read) VALUES (?, ?, ?, ?)", notifications)

    # --- KB Articles ---
    articles = [
        ('How to Connect to Campus Wi-Fi', 'IT Support',
         'To connect to the campus Wi-Fi network, follow these steps:\n\n1. Open your device\'s Wi-Fi settings\n2. Select the network "CampusNet-Secure"\n3. Enter your student/staff credentials (same as your portal login)\n4. Accept the security certificate when prompted\n5. You should now be connected\n\nTroubleshooting tips:\n- Forget the network and reconnect if facing issues\n- Make sure your portal password hasn\'t expired\n- Contact IT Support if the issue persists'),
        ('Fee Payment Process & Refund Policy', 'Accounts',
         'How to pay your semester fees:\n\n1. Log in to the Student Portal\n2. Navigate to "Fee Payment" under the Accounts section\n3. Select the semester and verify the amount\n4. Choose your payment method (Net Banking, UPI, Card)\n5. Complete the payment and save the transaction receipt\n\nRefund Policy:\n- Requests must be submitted within 15 days\n- Processing takes 7-10 business days\n- Partial refunds available for course withdrawals before the deadline'),
        ('Hostel Rules and Regulations', 'Hostel',
         'Important hostel rules for all residents:\n\n- Hostel gates close at 10:00 PM on weekdays and 11:00 PM on weekends\n- Overnight leave must be approved 24 hours in advance\n- Mess timings: Breakfast 7-9 AM, Lunch 12-2 PM, Dinner 7-9 PM\n- Room maintenance requests should be submitted through the helpdesk\n- Any damage to hostel property will be charged to the resident\n- Visitors allowed only in common area during visiting hours (4-6 PM)'),
        ('How to Check Exam Results', 'Academics',
         'To check your exam results:\n\n1. Log in to the Student Portal\n2. Go to "Academics" > "Results"\n3. Select the relevant semester\n4. Your grade card will be displayed\n\nIf you find any discrepancy:\n- Take a screenshot of the incorrect result\n- Submit a ticket through the Campus Helpdesk\n- Attach supporting documents\n- The academic office will review within 5-7 working days'),
        ('Password Reset Guide', 'IT Support',
         'If you\'ve forgotten your campus portal password:\n\n1. Go to the login page and click "Forgot Password"\n2. Enter your registered email or student ID\n3. You will receive an OTP on your registered mobile\n4. Enter the OTP and set a new password\n\nPassword requirements:\n- Minimum 8 characters\n- At least one uppercase, one number, one special character\n- Cannot reuse your last 3 passwords\n\nIf your account gets locked, contact IT Support.'),
    ]
    cur.executemany("INSERT INTO kb_articles (title, category, content) VALUES (?, ?, ?)", articles)

    con.commit()
    con.close()
    print("Database seeded successfully!")
    print()
    print("Demo Accounts:")
    print("  Admin:   admin / admin123")
    print("  Agent:   agent_priya / agent123")
    print("  Agent:   agent_rahul / agent123")
    print("  Student: student_aarav / student123")
    print("  Student: student_neha / student123")
    print("  Student: student_kabir / student123")

if __name__ == '__main__':
    seed()

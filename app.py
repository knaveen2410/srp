from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from flask_mysqldb import MySQL
from functools import wraps
import markdown
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config  # Import the Config class
import os  
from werkzeug.utils import secure_filename  # For secure file uploads
from flask import send_from_directory, abort
import time
import re
from flask_cors import CORS
import google.generativeai as genai
import requests
import PyPDF2
from flask import session


RESUME_FOLDER = 'static/resume'
app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.secret_key = 'your_secret_key'  # Secret key for session management

app.config.from_object(Config)
 
 
# Initialize MySQL
mysql = MySQL(app)

genai.configure(api_key="AIzaSyDJ_iTrvgujRk99QTMP3mJva4D4yliUdeU")
model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content("do u know Kola Naveen")
print(response.text)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        try:
            # Connect to MySQL and insert user data
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO users (name, username, email, password, role)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, username, email, password, role))

            # Commit the transaction to save the changes
            mysql.connection.commit()

            # Close the cursor
            cur.close()

            # Success message
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            # Handle any errors
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('signup'))

    return render_template('signup.html')



# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and user['password'] == password:  # Check the actual password
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['logged_in'] = True
            flash('Login successful!', 'success')
            
            # Redirect based on role
            if user['role'] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'HR Manager':
                return redirect(url_for('hr_dashboard'))
            elif user['role'] == 'Recruiter':
                return redirect(url_for('recruiter_dashboard'))
            elif user['role'] == 'Interviewer':
                return redirect(url_for('interviewer_dashboard'))
            elif user['role'] == 'Candidate':
                return redirect(url_for('candidate_dashboard'))
            else:
                flash('Role not recognized.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Login required decorator for role-based access
def login_required(roles=None):
    if roles is None:
        roles = []

    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                flash('You need to log in first!', 'danger')
                return redirect(url_for('login'))
            if roles and session.get('role') not in roles:
                flash('You do not have access to this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper


# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

# Dashboard route
@app.route('/dashboard')
@login_required()
def dashboard():
    return render_template('dashboard.html')

# Admin dashboard
@app.route('/admin-dashboard')
@login_required(roles=["Admin"])
def admin_dashboard():
    cur = mysql.connection.cursor()
    
    # Fetch totals
    cur.execute("SELECT COUNT(*) AS total FROM job_postings")
    total_jobs = cur.fetchone()  # Get the first result
    total_jobs_count = total_jobs['total'] if total_jobs else 0  # Use dictionary-like access

    cur.execute("SELECT COUNT(*) AS total FROM applications")
    total_applications = cur.fetchone()
    total_applications_count = total_applications['total'] if total_applications else 0  # Use dictionary-like access

    cur.execute("SELECT COUNT(*) AS total FROM interview_schedule")
    total_interviews = cur.fetchone()
    total_interviews_count = total_interviews['total'] if total_interviews else 0  # Use dictionary-like access
    # Get the total number of candidates
    cur.execute("SELECT COUNT(*) AS total FROM Users WHERE role = 'candidate'")
    total_candidates = cur.fetchone()
    total_candidates_count = total_candidates['total'] if total_candidates else 0

    # Get the total number of interviewers
    cur.execute("SELECT COUNT(*) AS total FROM Users WHERE role = 'interviewer'")
    total_interviewers = cur.fetchone()
    total_interviewers_count = total_interviewers['total'] if total_interviewers else 0
    
    # Fetch job postings
    cur.execute("SELECT * FROM job_postings")  # Make sure to use the correct table name
    job_postings = cur.fetchall()  # Fetch all job postings

    try:
        # Fetch applications and join with users and job_postings for details
        cur.execute("""
            SELECT applications.id, users.name AS applicant_name, job_postings.job_title, applications.status,applications.resume
            FROM applications
            JOIN users ON applications.candidate_id = users.id
            JOIN job_postings ON applications.job_id = job_postings.id
        """)
        applications = cur.fetchall()
    except Exception as e:
        print(f"Error fetching applications: {e}")
        applications = []  # Fallback to empty list if there's an error
    finally:
        cur.close()  # Ensure the cursor is closed even if an error occurs
    
    cur.close()
    
    return render_template(
        'admin_dashboard.html', 
        total_jobs=total_jobs_count, 
        total_applications=total_applications_count, 
        total_interviews=total_interviews_count,
        total_candidates = total_candidates_count,
        total_interviewers = total_interviewers_count,
        applications=applications,
        job_postings=job_postings, 
        username=session.get('username'),
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    

# HR dashboard
@app.route('/hr-dashboard')
@login_required(roles=["HR Manager"])
def hr_dashboard():
    cur = mysql.connection.cursor()
    
    # Fetch totals
    cur.execute("SELECT COUNT(*) AS total FROM job_postings")
    total_jobs = cur.fetchone()  # Get the first result
    total_jobs_count = total_jobs['total'] if total_jobs else 0  # Use dictionary-like access

    cur.execute("SELECT COUNT(*) AS total FROM applications")
    total_applications = cur.fetchone()
    total_applications_count = total_applications['total'] if total_applications else 0  # Use dictionary-like access

    cur.execute("SELECT COUNT(*) AS total FROM interview_schedule")
    total_interviews = cur.fetchone()
    total_interviews_count = total_interviews['total'] if total_interviews else 0  # Use dictionary-like access
    # Get the total number of candidates
    cur.execute("SELECT COUNT(*) AS total FROM Users WHERE role = 'candidate'")
    total_candidates = cur.fetchone()
    total_candidates_count = total_candidates['total'] if total_candidates else 0

    # Get the total number of interviewers
    cur.execute("SELECT COUNT(*) AS total FROM Users WHERE role = 'interviewer'")
    total_interviewers = cur.fetchone()
    total_interviewers_count = total_interviewers['total'] if total_interviewers else 0
    
    # Fetch job postings
    cur.execute("SELECT * FROM job_postings")  # Make sure to use the correct table name
    job_postings = cur.fetchall()  # Fetch all job postings
    
    cur = mysql.connection.cursor()

    try:
        # Fetch applications and join with users and job_postings for details
        cur.execute("""
            SELECT applications.id, users.name AS applicant_name, job_postings.job_title, applications.status,applications.resume
            FROM applications
            JOIN users ON applications.candidate_id = users.id
            JOIN job_postings ON applications.job_id = job_postings.id
        """)
        applications = cur.fetchall()
    except Exception as e:
        print(f"Error fetching applications: {e}")
        applications = []  # Fallback to empty list if there's an error
    finally:
        cur.close()  # Ensure the cursor is closed even if an error occurs
    
    cur.close()
    
    return render_template(
        'hr_dashboard.html', 
        total_jobs=total_jobs_count, 
        total_applications=total_applications_count, 
        total_interviews=total_interviews_count,
        total_candidates = total_candidates_count,
        total_interviewers = total_interviewers_count,
        applications=applications,
        job_postings=job_postings,  # Pass the job postings to the template
        username=session.get('username'), 
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


# Recruiter dashboard
@app.route('/recruiter-dashboard')
@login_required(roles=["Recruiter"])
def recruiter_dashboard():
    cur = mysql.connection.cursor()
    
    # Total Job Openings: Count of active jobs
    total_job_openings_query = "SELECT COUNT(*) AS total_job_openings FROM job_postings;"
    cur.execute(total_job_openings_query)
    total_job_openings = cur.fetchone()['total_job_openings']
    
    # Total Applications: Count of applications received
    total_applications_query = "SELECT COUNT(*) AS total_applications FROM applications;"
    cur.execute(total_applications_query)
    total_applications = cur.fetchone()['total_applications']
    
    # Applications by Status
    applications_by_status_query = """
    SELECT status, COUNT(*) AS count 
    FROM applications 
    GROUP BY status;
    """
    cur.execute(applications_by_status_query)
    applications_by_status = cur.fetchall()
    
    # Total Interviews Scheduled
    total_interviews_query = "SELECT COUNT(*) AS total_interviews FROM interview_schedule;"
    cur.execute(total_interviews_query)
    total_interviews = cur.fetchone()['total_interviews']
    
    # Applications by Job Posting
    applications_by_job_query = """
    SELECT jp.job_title, COUNT(a.id) AS application_count 
    FROM applications a
    JOIN job_postings jp ON a.job_id = jp.id
    GROUP BY jp.job_title;
    """
    cur.execute(applications_by_job_query)
    applications_by_job = cur.fetchall()
    
    # Candidate Evaluation Status
    candidate_evaluation_status_query = """
SELECT selection_status, COUNT(*) AS count 
FROM interview_feedback 
GROUP BY selection_status;
"""
    cur.execute(candidate_evaluation_status_query)
    candidate_evaluation_status = cur.fetchall()
    
    # Candidates who are Selected
    selected_candidates_query = """
SELECT a.candidate_name 
FROM interview_feedback f
JOIN interview_schedule i ON f.interview_schedule_id = i.id
JOIN applications a ON i.application_id = a.id
WHERE f.selection_status = 'Selected';
"""
    cur.execute(selected_candidates_query)
    selected_candidates = cur.fetchall()
    # Job Postings
    job_postings_query = """
    SELECT job_title, job_description, department, job_location
    FROM job_postings;
    """
    cur.execute(job_postings_query)
    job_postings = cur.fetchall()

    # Applications
    applications_query = """
    SELECT 
        a.candidate_name,
        a.resume,
        DATE_FORMAT(a.dob, '%d-%m-%Y') AS dob,
        jp.job_title
    FROM 
        applications a
    JOIN 
        job_postings jp ON a.job_id = jp.id;
    """
    cur.execute(applications_query)
    applications = cur.fetchall()

    # Interviews
    interviews_query = """
    SELECT 
        jp.job_title,
        a.candidate_name,
        resume,
        address,
        i.interview_date,
        GROUP_CONCAT(u.name SEPARATOR ', ') AS interviewer_names
    FROM 
        interview_schedule i
    JOIN 
        applications a ON i.application_id = a.id
    JOIN 
        job_postings jp ON a.job_id = jp.id
    JOIN 
        users u ON FIND_IN_SET(u.id, i.interviewers) > 0
    GROUP BY 
        i.id;
    """
    cur.execute(interviews_query)
    interviews = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS offers_made FROM interview_feedback WHERE selection_status = 'Selected';")
    offers_made = cur.fetchone()['offers_made']

    
    cur.close()
    
    # Render the template with the fetched data
    return render_template('recruiter_dashboard.html',
                           total_job_openings=total_job_openings,
                           total_applications=total_applications,
                           applications_by_status=applications_by_status,
                           total_interviews=total_interviews,
                           applications_by_job=applications_by_job,
                           job_postings=job_postings,
                           applications=applications,
                           interviews=interviews,
                           candidate_evaluation_status=candidate_evaluation_status,
                           selected_candidates=selected_candidates,
                           offers_made = offers_made,
                           username=session.get('username'),
                           current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# Interviewer dashboard
@app.route('/interviewer-dashboard')
@login_required(roles=["Interviewer"])
def interviewer_dashboard():
    cur = mysql.connection.cursor()
    
    # Query to fetch interview schedules along with candidate names
    query = """
       SELECT 
    i.id AS interview_id,
    i.application_id,
    i.interview_date,
    i.interview_time,
    GROUP_CONCAT(u.name SEPARATOR ', ') AS interviewer_names,
    a.candidate_name
FROM 
    interview_schedule i
JOIN 
    applications a ON i.application_id = a.id
JOIN 
    users u ON FIND_IN_SET(u.id, i.interviewers) > 0
GROUP BY 
    i.id;


    """
    cur.execute(query)
    schedules = cur.fetchall()
    cur.close()
    
    return render_template('interviewer_dashboard.html', schedules=schedules,
                           username=session.get('username'),
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


# Candidate dashboard
@app.route('/candidate-dashboard',methods=['GET', 'POST'])
@login_required(roles=["Candidate"])
def candidate_dashboard():
    candidate_id = session.get('user_id')
    username = session.get('username')  # Get the username from the session
    name = session.get('name')
    cur = mysql.connection.cursor()
    
    # Fetch all job postings
    cur.execute("SELECT * FROM job_postings")  
    job_postings = cur.fetchall()  
    
    # Fetch applied jobs for the current candidate
    cur.execute("SELECT job_id FROM applications WHERE candidate_name = %s", (username,))
    applied_jobs = {job['job_id'] for job in cur.fetchall()}  
    cur.execute("""
    SELECT i.*, a.candidate_id, u.name AS candidate_name, interviewer.name AS interviewer_name
    FROM interview_schedule i
    JOIN applications a ON i.application_id = a.id
    JOIN users u ON a.candidate_id = u.id
    JOIN users interviewer ON i.interviewers = interviewer.id
""")

    upcoming_interviews = cur.fetchall()
    
    query = """
        SELECT a.*, j.job_title 
        FROM applications a 
        JOIN job_postings j ON a.job_id = j.id 
        WHERE a.candidate_id = %s
    """
    cur.execute(query, (candidate_id,))
    applications = cur.fetchall()
    
    
    cur.close()
    
    return render_template(
        'candidate_dashboard.html',
        job_postings=job_postings,  
        applied_jobs=applied_jobs,
        applications=applications,
        interviews=upcoming_interviews,  # Pass the list of upcoming interviews to the template
        username=username, 
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


# Route to create a job


# Route to create a job
@app.route('/create_job', methods=['GET', 'POST'])
@login_required(roles=["HR Manager", "Admin"])
def create_job():
    if request.method == 'POST':
        job_title = request.form['job_title']
        job_description = request.form['job_description']
        department = request.form['department']
        job_location = request.form['job_location']
        employment_type = request.form['employment_type']
        salary_range = request.form['salary_range']
        application_deadline = request.form['application_deadline']
        required_qualifications = request.form['required_qualifications']
        preferred_qualifications = request.form['preferred_qualifications']
        responsibilities = request.form['responsibilities']
        action = request.form['action']

        # Validate the deadline
        if datetime.strptime(application_deadline, '%Y-%m-%d') <= datetime.now():
            flash('Application deadline must be a future date.', 'danger')
            return redirect(url_for('create_job'))

        # Set status based on action
        status = "Draft" if action == "Save as Draft" else "Published"

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO job_postings (job_title, job_description, department, job_location, employment_type, salary_range, application_deadline, required_qualifications, preferred_qualifications, responsibilities, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (job_title, job_description, department, job_location, employment_type, salary_range, application_deadline, required_qualifications, preferred_qualifications, responsibilities, status)
        )
        mysql.connection.commit()
        cur.close()

        flash(f'Job posting {"saved as draft" if action == "Save as Draft" else "published"} successfully!', 'success')

        # Redirect based on role from session
        if session.get('role') == "Admin":
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('hr_dashboard'))

    return render_template('create_job.html')


# Route to edit a job posting (HR Manager only)
@app.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
@login_required(roles=["HR Manager","Admin","Recruiter"])
def edit_job(job_id):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        job_title = request.form['job_title']
        job_description = request.form['job_description']
        department = request.form['department']
        job_location = request.form['job_location']
        employment_type = request.form['employment_type']
        salary_range = request.form['salary_range']
        application_deadline = request.form['application_deadline']
        required_qualifications = request.form['required_qualifications']
        preferred_qualifications = request.form['preferred_qualifications']
        responsibilities = request.form['responsibilities']
        action = request.form['action']

        # Update the job posting in the database
        cur.execute("""
            UPDATE job_postings 
            SET job_title=%s, job_description=%s, department=%s, job_location=%s, 
                employment_type=%s, salary_range=%s, application_deadline=%s, 
                required_qualifications=%s, preferred_qualifications=%s, 
                responsibilities=%s, status=%s
            WHERE id=%s
        """, (job_title, job_description, department, job_location, employment_type,
              salary_range, application_deadline, required_qualifications,
              preferred_qualifications, responsibilities, action, job_id))

        mysql.connection.commit()
        cur.close()

        flash('Job posting updated successfully!', 'success')
        return redirect(url_for('view_jobs'))

    # GET request: Fetch the current job details
    cur.execute("SELECT * FROM job_postings WHERE id = %s", (job_id,))
    job = cur.fetchone()
    cur.close()

    return render_template('edit_job.html', job=job)
# Route to delete a job posting (HR Manager only)
@app.route('/delete_job/<int:job_id>', methods=['POST'])
@login_required(roles=["HR Manager", "Admin"])
def delete_job(job_id):
    try:
        cur = mysql.connection.cursor()

        # Delete associated applications first
        cur.execute("DELETE FROM applications WHERE job_id = %s", (job_id,))
        
        # Now delete the job posting
        cur.execute("DELETE FROM job_postings WHERE id = %s", (job_id,))
        
        mysql.connection.commit()  # Commit changes
        cur.close()

        flash('Job posting deleted successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()  # Rollback in case of error
        flash(f'Error deleting job posting: {str(e)}', 'danger')

    user_role = session.get('role')
    if user_role == "Admin":
        return redirect(url_for('admin_dashboard'))
    elif user_role == "HR Manager":
        return redirect(url_for('hr_dashboard'))
    else:
        return redirect(url_for('default_dashboard'))




@app.route('/view_jobs')
@login_required(roles=["HR Manager", "Admin", "Candidate"])
def view_jobs():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM job_postings")
    job_postings = cur.fetchall()
    cur.close()

    return render_template('view_jobs.html', job_postings=job_postings)


@app.route('/view_application/<int:application_id>')
@login_required(roles=["HR Manager", "Admin","Interviewer"])
def view_application(application_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM applications WHERE id = %s", (application_id,))
    application = cur.fetchone()
    cur.close()

    if application:
        return render_template('view_application.html', application=application)
    else:
        return "Application not found", 404


@app.route('/approve_application/<int:application_id>', methods=['POST'])
@login_required(roles=["HR Manager","Admin"])
def approve_application(application_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE applications SET status = 'Approved' WHERE id = %s", (application_id,))
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('my_applications'))

@app.route('/reject_application/<int:application_id>', methods=['POST'])
@login_required(roles=["HR Manager","Admin"])
def reject_application(application_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE applications SET status = 'Rejected' WHERE id = %s", (application_id,))
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('my_applications'))

@app.route('/edit_application/<int:application_id>', methods=['GET', 'POST'])
@login_required(roles=["HR Manager", "Admin"])
def edit_application(application_id):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        candidate_name = request.form['candidate_name']
        job_title = request.form['job_title']
        status = request.form['status']
        
        cur.execute("""
            UPDATE applications
            SET candidate_name = %s, job_title = %s, status = %s
            WHERE id = %s
        """, (candidate_name, job_title, status, application_id))
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('view_applications'))

    cur.execute("SELECT * FROM applications WHERE id = %s", (application_id,))
    application = cur.fetchone()
    cur.close()
    
    return render_template('edit_application.html', application=application)


@app.route('/delete_application/<int:application_id>', methods=['POST'])
@login_required(roles=["HR Manager", "Admin"])
def delete_application(application_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM applications WHERE id = %s", (application_id,))
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('view_applications'))


@app.route('/delete_applications', methods=['POST'])
@login_required(roles=["HR Manager", "Admin","Candidate"])
def delete_applications():
    application_ids = request.form.getlist('application_ids')  # Get the list of application IDs from the form
    if not application_ids:
        flash("No application IDs provided.", "danger")
        return redirect(url_for('view_applications'))

    try:
        with mysql.connection.cursor() as cur:
            # First, delete feedback records in interview_feedback
            format_strings = ','.join(['%s'] * len(application_ids))
            cur.execute(f"""
                DELETE FROM interview_feedback 
                WHERE interview_schedule_id IN (
                    SELECT id FROM interview_schedule WHERE application_id IN ({format_strings})
                )
            """, tuple(application_ids))
            
            # Now delete dependent rows in interview_schedule
            cur.execute(f"DELETE FROM interview_schedule WHERE application_id IN ({format_strings})", tuple(application_ids))
            
            # Finally, delete from applications
            cur.execute(f"DELETE FROM applications WHERE id IN ({format_strings})", tuple(application_ids))
            mysql.connection.commit()

        flash("Applications and related schedules and feedback deleted successfully.", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting applications: {str(e)}", "danger")

    return redirect(url_for('view_applications'))



# Route for interview schedule (Interviewer only)
@app.route('/interview_schedule')
@login_required(roles=["Interviewer"])  # Ensures only interviewers can access this route
def interview_schedule():
    cur = mysql.connection.cursor()
    
    # Query to fetch interview schedules along with candidate names
    query = """
        SELECT s.*, a.candidate_id, u.name AS candidate_name
        FROM interview_schedule s
        JOIN applications a ON s.application_id = a.id
        JOIN users u ON a.candidate_id = u.id
    """
    cur.execute(query)
    schedules = cur.fetchall()
    cur.close()
    
    return render_template('interview_schedule.html', schedules=schedules)



@app.route('/schedule_interview/<int:application_id>', methods=['GET', 'POST'])
@login_required(roles=["HR Manager", "Admin", "Interviewer"])
def schedule_interview(application_id):
    cur = mysql.connection.cursor()

    # Fetch interviewers from the database
    cur.execute("SELECT id, name FROM users WHERE role = 'Interviewer'")
    interviewers = cur.fetchall()  # Fetch all interviewers

    if request.method == 'POST':
        interview_date = request.form['interview_date']
        interview_time = request.form['interview_time']
        selected_interviewers = request.form.getlist('interviewers')  # Get selected interviewers as a list
        
        # Convert the list of selected interviewers to a comma-separated string
        interviewers_string = ', '.join(selected_interviewers)

        cur.execute(
            "INSERT INTO interview_schedule (application_id, interview_date, interview_time, interviewers) VALUES (%s, %s, %s, %s)", 
            (application_id, interview_date, interview_time, interviewers_string)
        )
        mysql.connection.commit()
        cur.close()

        # Assuming 'session' holds the user's information, including their role.
        if session['role'] == 'HR Manager':
            flash('Interview scheduled successfully!', 'success')
            return redirect(url_for('hr_dashboard'))  # Redirect to HR Dashboard
        elif session['role'] == 'Admin':
            flash('Interview scheduled successfully!', 'success')
            return redirect(url_for('admin_dashboard'))  # Redirect to Admin Dashboard
        elif session['role'] == 'Interviewer':
            flash('Interview scheduled successfully!', 'success')
            return redirect(url_for('interviewer_dashboard'))  # Redirect to Interviewer Dashboard
        else:
            flash('Interview scheduled successfully!', 'success')
            return redirect(url_for('default_dashboard'))  # Redirect to a default dashboard if role doesn't match


    cur.close()
    return render_template('schedule_interview.html', application_id=application_id, interviewers=interviewers)


@app.route('/edit_interview/<int:interview_id>', methods=['GET', 'POST'])
@login_required(roles=["HR Manager", "Interviewer", "Admin","Recruiter"])
def edit_interview(interview_id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        interview_date = request.form['interview_date']
        interview_time = request.form['interview_time']
        selected_interviewers = request.form.getlist('interviewers')  # Get multiple selected interviewers
        
        # Convert the list of selected interviewers to a comma-separated string
        interviewers_string = ', '.join(selected_interviewers)

        cur.execute("""
            UPDATE interview_schedule
            SET interview_date = %s, interview_time = %s, interviewers = %s
            WHERE id = %s
        """, (interview_date, interview_time, interviewers_string, interview_id))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('view_interviews'))

    # Fetch the existing interview details
    cur.execute("SELECT * FROM interview_schedule WHERE id = %s", (interview_id,))
    interview = cur.fetchone()

    # Fetch interviewers from the database
    cur.execute("SELECT id, name FROM users WHERE role = 'Interviewer'")
    interviewers = cur.fetchall()  # Fetch all interviewers

    cur.close()

    return render_template('edit_interview.html', interview=interview, interviewers=interviewers)






@app.route('/view_interviews')
@login_required(roles=["HR Manager", "Interviewer","Recruiter"])
def view_interviews():
    cur = mysql.connection.cursor()
    
    # Fetch interviews along with candidate names
    cur.execute("""
    SELECT i.*, a.candidate_id, u.name AS candidate_name, interviewer.name AS interviewer_name
    FROM interview_schedule i
    JOIN applications a ON i.application_id = a.id
    JOIN users u ON a.candidate_id = u.id
    JOIN users interviewer ON i.interviewers = interviewer.id
""")

    
    interviews = cur.fetchall()
    cur.close()
    
    return render_template('view_interviews.html', interviews=interviews)



@app.route('/delete_interview/<int:interview_id>', methods=['POST'])
@login_required(roles=["HR Manager", "Admin", "Interviewer","Recruiter"])
def delete_interview(interview_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM interview_schedule WHERE id = %s", (interview_id,))
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('view_interviews'))

@app.route('/update_interview_status/<int:interview_id>', methods=['POST'])
@login_required(roles=["HR Manager", "Admin", "Interviewer"])
def update_interview_status(interview_id):
    status = request.form['status']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE interview_schedule SET status = %s WHERE id = %s", (status, interview_id))
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('view_interviews'))




@app.route('/generate_reports')
@login_required(roles=["HR Manager", "Admin"])
def generate_reports():
    cur = mysql.connection.cursor()

    # Query 1: Total number of job applications
    cur.execute("SELECT COUNT(*) AS total_applications FROM applications")
    total_applications = cur.fetchone()

    # Query 2: Applications per job
    cur.execute("""
        SELECT jp.id AS job_id, jp.job_title, COUNT(a.id) AS applications_count
        FROM job_postings jp
        LEFT JOIN applications a ON jp.id = a.job_id
        GROUP BY jp.id, jp.job_title
    """)
    applications_per_job = cur.fetchall()

    # Query 3: Applications by status
    cur.execute("""
        SELECT status, COUNT(*) AS status_count
        FROM applications
        GROUP BY status
    """)
    applications_by_status = cur.fetchall()

    # Query 4: Total number of interviews scheduled
    cur.execute("SELECT COUNT(*) AS total_interviews FROM interview_schedule")
    total_interviews = cur.fetchone()

    # Query 5: Users by role
    cur.execute("""
        SELECT role, COUNT(*) AS role_count
        FROM users
        GROUP BY role
    """)
    users_by_role = cur.fetchall()

    # Query 6: Total number of job postings
    cur.execute("SELECT COUNT(*) AS total_job_postings FROM job_postings")
    total_job_postings = cur.fetchone()

    # Query 7: Recent applications with candidate details
    cur.execute("""
        SELECT a.id AS application_id, a.candidate_name, a.job_id, a.submission_date, j.job_title
        FROM applications AS a
        JOIN job_postings AS j ON a.job_id = j.id
        ORDER BY a.submission_date DESC
        LIMIT 10
    """)
    recent_applications = cur.fetchall()

    # Query 8: Upcoming interview schedules
    cur.execute("""
        SELECT isch.id AS interview_id, a.candidate_name, isch.interview_date, isch.interview_time, isch.interviewers
        FROM interview_schedule AS isch
        JOIN applications AS a ON isch.application_id = a.id
        WHERE isch.interview_date >= NOW()
        ORDER BY isch.interview_date ASC
    """)
    upcoming_interviews = cur.fetchall()

    # Query 9: Job postings report
    cur.execute("""
        SELECT jp.id AS job_id, jp.job_title, jp.department, jp.job_location, jp.status, jp.created_at
        FROM job_postings AS jp
        ORDER BY jp.created_at DESC
    """)
    job_postings = cur.fetchall()

    # Query 10: Application status counts
    cur.execute("""
        SELECT status, COUNT(*) AS count
        FROM applications
        GROUP BY status
    """)
    application_status_counts = cur.fetchall()

    # Query 11: Candidates with job applications
    cur.execute("""
        SELECT a.candidate_name, a.job_id, j.job_title, a.status, a.submission_date
        FROM applications AS a
        JOIN job_postings AS j ON a.job_id = j.id
        ORDER BY a.submission_date DESC
    """)
    candidates_with_applications = cur.fetchall()

    cur.close()

    # Pass all data to template
    return render_template(
        'generate_reports.html',
        total_applications=total_applications,
        applications_per_job=applications_per_job,
        applications_by_status=applications_by_status,
        total_interviews=total_interviews,
        users_by_role=users_by_role,
        total_job_postings=total_job_postings,
        recent_applications=recent_applications,
        upcoming_interviews=upcoming_interviews,
        job_postings=job_postings,
        application_status_counts=application_status_counts,
        candidates_with_applications=candidates_with_applications
    )
    



@app.route('/update_application_status/<int:application_id>', methods=['GET', 'POST'])
@login_required(roles=["HR Manager", "Admin"])
def update_application_status(application_id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        new_status = request.form['status']
        
        # Update the status in the database
        cur.execute("UPDATE applications SET status = %s WHERE id = %s", (new_status, application_id))
        mysql.connection.commit()
        cur.close()
        
        # Role-based redirect
        user_role = session.get('role')
        if user_role == "Admin":
            return redirect(url_for('admin_dashboard'))
        elif user_role == "HR Manager":
            return redirect(url_for('hr_dashboard'))
        else:
            return redirect(url_for('default_dashboard'))  # Optional for other roles

    # Fetch the current application status
    cur.execute("SELECT status FROM applications WHERE id = %s", (application_id,))
    current_status = cur.fetchone()
    cur.close()

    return render_template('update_application_status.html', application_id=application_id, current_status=current_status)
@app.route('/candidates')
@login_required(roles=["HR Manager", "Admin"])
def candidates():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM applications WHERE status = 'Hired'")
    candidates = cur.fetchall()
    cur.close()
    
    return render_template('candidates.html', candidates=candidates)

@app.route('/view_candidates')

@login_required(roles=["HR Manager", "Admin","Interviewer","Recruiter"])
def view_candidates():
    cur = mysql.connection.cursor()
    
    cur.execute("SELECT name, username, email,number FROM users WHERE role='Admin' ORDER BY lower(name) ASC")
    admins = cur.fetchall()
    
    cur.execute("SELECT name, username, email,number FROM users WHERE role='HR Manager' ORDER BY lower(name) ASC")
    hrs = cur.fetchall()
    
    cur.execute("SELECT name, username, email,number FROM users WHERE role='Interviewer' ORDER BY lower(name) ASC")
    interviewers = cur.fetchall()
    
    cur.execute("SELECT name, username, email,number FROM users WHERE role='Recruiter' ORDER BY lower(name) ASC")
    recruiters = cur.fetchall()
    
    cur.execute("SELECT name, username, email,number  FROM users WHERE role='Candidate' ORDER BY lower(name) ASC")
    candidates = cur.fetchall()
    cur.close()

    return render_template('view_candidates.html', 
                           candidates=candidates,
                           admins=admins,
                           hrs=hrs,
                           interviewers=interviewers,
                           recruiters=recruiters
                           )


@app.route('/delete_candidate/<int:application_id>', methods=['POST'])
@login_required(roles=["HR Manager", "Admin"])
def delete_candidate(application_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM applications WHERE id = %s", (application_id,))
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('candidates'))

@app.route('/submit_feedback/<int:interview_schedule_id>', methods=['GET', 'POST'])
@login_required(roles=["Interviewer"])
def submit_feedback(interview_schedule_id):
    if request.method == 'POST':
        feedback = request.form.get('feedback', '').strip()  # Get the feedback input
        rating = request.form.get('rating', type=int)  # Get the rating input
        name = request.form.get('name', '').strip()  # Get the name input
        selection_status = request.form.get('selection_status', 'On Hold')  # Default selection status

        # Check for any empty required fields
        if not feedback or not name or rating is None:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('submit_feedback', interview_schedule_id=interview_schedule_id))

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO interview_feedback (interview_schedule_id, feedback, rating, name, selection_status) 
                VALUES (%s, %s, %s, %s, %s)
            """, (interview_schedule_id, feedback, rating, name, selection_status))
            mysql.connection.commit()
            flash('Feedback submitted successfully!', 'success')
        except Exception as e:
            mysql.connection.rollback()  # Rollback in case of error
            flash(f'An error occurred: {str(e)}', 'danger')
        finally:
            cur.close()

        return redirect(url_for('interviewer_dashboard'))

    return render_template('submit_feedback.html', interview_schedule_id=interview_schedule_id)



@app.route('/evaluate_candidate/<int:application_id>', methods=['GET', 'POST'])
@login_required(roles=["HR Manager", "Admin"])
def evaluate_candidate(application_id):
    if request.method == 'POST':
        feedback = request.form['feedback']
        rating = request.form['rating']
        selection_status = request.form['selection_status']
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO candidate_evaluations (application_id, feedback, rating, selection_status) VALUES (%s, %s, %s, %s)",
                    (application_id, feedback, rating, selection_status))
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('my_applications'))

    return render_template('evaluate_candidate.html', application_id=application_id)

@app.route('/job_postings')
def job_postings():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM job_postings WHERE status = 'Published'")
    jobs = cur.fetchall()
    cur.close()
    return render_template('job_postings.html', jobs=jobs)


@app.route('/apply-job/<int:job_id>', methods=['GET', 'POST'])
@login_required(roles=["Candidate"])
def apply_job(job_id):
    cur = mysql.connection.cursor()
    
    # Fetch all job details for the job being applied to
    cur.execute("""
        SELECT job_title, job_description, department, job_location, employment_type, 
               salary_range, application_deadline, required_qualifications, 
               preferred_qualifications, responsibilities 
        FROM job_postings 
        WHERE id = %s
    """, (job_id,))
    
    job = cur.fetchone()
    if job:
        job_title = job['job_title']
        job_description = job['job_description']
        department = job['department']
        job_location = job['job_location']
        employment_type = job['employment_type']
        salary_range = job['salary_range']
        application_deadline = job['application_deadline']
        required_qualifications = job['required_qualifications']
        preferred_qualifications = job['preferred_qualifications']
        responsibilities = job['responsibilities']
    else:
        flash('Job not found', 'error')
        return redirect(url_for('job_list'))  # Change this to your job listing route

    if request.method == 'POST':
        try:
            candidate_name = request.form['candidate_name']
            dob = request.form['dob']
            resume = request.files['resume']
            address = request.form['address']
            phone_number = request.form['phone_number']
        except KeyError as e:
            flash(f'Missing field: {str(e)}', 'error')
            return redirect(url_for('apply_job', job_id=job_id))
        
        # Ensure the resume folder exists
        if not os.path.exists(RESUME_FOLDER):
            os.makedirs(RESUME_FOLDER)  # Create the directory if it doesn't exist
        
        # Save resume file to the designated folder
        resume_filename = secure_filename(resume.filename)
        resume.save(os.path.join(RESUME_FOLDER, resume_filename))  # Save the file
        
        # Insert application details into the database
        cur.execute("""
            INSERT INTO applications (job_id, candidate_id, candidate_name, dob, resume, address, phone_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (job_id, session.get('user_id'), candidate_name, dob, resume_filename, address, phone_number))

        # Optionally update the job status
        cur.execute("""
            UPDATE job_postings SET status = 'Applied' WHERE id = %s
        """, (job_id,))

        mysql.connection.commit()
        cur.close()
        
        flash('Application submitted successfully!')  # Set success message
        return redirect(url_for('candidate_dashboard'))  # Redirect to the candidate dashboard

    cur.close()
    return render_template('application_form.html', job_title=job_title, job_description=job_description,
                           department=department, job_location=job_location, employment_type=employment_type,
                           salary_range=salary_range, application_deadline=application_deadline,
                           required_qualifications=required_qualifications, 
                           preferred_qualifications=preferred_qualifications,
                           responsibilities=responsibilities, job_id=job_id)



@app.route('/my_applications')
@login_required(roles=["Candidate"])
def my_applications():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM applications WHERE applicant_name = %s", (session['user'],))
    applications = cur.fetchall()
    cur.close()
    return render_template('my_applications.html', applications=applications)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required(roles=["Candidate"])
def edit_profile():
    cur = mysql.connection.cursor()
    
    # Use the correct session key for username
    username = session.get('username')  # Make sure this matches your session setup

    # Fetch the current user's profile information
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()

    if request.method == 'POST':
        # Collect new profile data from the form
        new_name = request.form['applicant_name']
        new_email = request.form['email']
        new_phone = request.form['phone']  # Assuming you have this field
        new_address = request.form['address']  # Assuming you have this field
        new_dob = request.form['date_of_birth']  # Assuming you have this field
        # Add other fields as necessary
        
        # Update the database with the new information
        cur.execute("""
            UPDATE users 
            SET name = %s, email = %s, phone = %s, address = %s, date_of_birth = %s 
            WHERE username = %s
        """, (new_name, new_email, new_phone, new_address, new_dob, username))
        
        mysql.connection.commit()

        # Optionally, update the session data
        session['user_name'] = new_name  # Update session if you're storing name in session
        
        flash('Profile updated successfully!', 'success')  # Flash a success message
        return redirect(url_for('dashboard'))  # Redirect to the dashboard or a different page

    cur.close()
    return render_template('edit_profile.html', user=user)

@app.route('/view_resume/<filename>')
def view_resume(filename):
    resume_directory = os.path.join(app.root_path, 'static', 'resume')
    # Check if the file exists in the directory
    if os.path.exists(os.path.join(resume_directory, filename)):
        return send_from_directory(resume_directory, filename)
    else:
        abort(404)  # File not found
        
        
@app.route('/candidate_feedback')
@login_required(roles=["Candidate"])
def candidate_feedback():
    cur = mysql.connection.cursor()
    query = """
        SELECT 
            f.name,
            f.feedback,
            f.rating,
            f.selection_status
        FROM interview_feedback f
        JOIN users u ON f.name = u.name
        WHERE u.role = 'Candidate';
    """
    cur.execute(query)
    feedback_data = cur.fetchall()
    cur.close()
    
    return render_template('candidate_feedback.html', feedback_data=feedback_data)


#AI Implementation
def read_pdf(file_path):
    text = ''
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + '\n'
    return text

def clean_text(parsed_text):
    # Remove markdown formatting
    cleaned_text = parsed_text.replace("**", "").replace("*", "").replace("\n", "<br>")
    return cleaned_text.strip()


@app.route('/upload', methods=['GET', 'POST'])
def upload_resume():
    parsed_text = None
    if request.method == 'POST':
        if 'resume' not in request.files:
            return "No file uploaded", 400

        resume_file = request.files['resume']

        # Save the uploaded file temporarily
        file_path = f"./uploads/{resume_file.filename}"
        resume_file.save(file_path)

        # Determine the file type and read accordingly
        if resume_file.filename.endswith('.pdf'):
            resume_text = read_pdf(file_path)
        else:
            # For .txt and other text files, read normally
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                resume_text = file.read()

        # Define your prompt for analysis
        # Define your prompt for analysis
        prompt = """Provide a brief evaluation of the resume below, including an overall score out of 100. Focus on:

1. **Content Quality**: Relevance of the experience, skills, and education listed.
2. **Presentation**: Clarity, formatting, and grammar.
3. **Professional Impression**: Overall impression of the candidate’s qualifications.

Give a score out of 100, followed by:
- 3 strengths of the resume
- 3 areas for improvement
- 3 specific suggestions to enhance the resume

Here is the resume text:


"""


        # Combine the prompt with the resume text
        full_prompt = prompt + resume_text

        # Generate response using Gemini AI
        response = model.generate_content(full_prompt)
        parsed_text = response.text
        parsed_text = clean_text(parsed_text)
        
        # Optionally remove the uploaded file after processing
        os.remove(file_path)

    return render_template('upload_resume.html', parsed_text=parsed_text)

# AIzaSyDJ_iTrvgujRk99QTMP3mJva4D4yliUdeU




def remove_br_tags(text):
    # Replace <br> or <br/> tags with a newline
    return re.sub(r'<br\s*/?>', '\n\n', text)

@app.route('/uploadResume', methods=['GET', 'POST'])
def uploadResume():
    score = None
    key_points = []

    if request.method == 'POST':
        if 'resume' not in request.files:
            return "No file uploaded", 400

        resume_file = request.files['resume']
        file_path = f"./uploads/{resume_file.filename}"
        resume_file.save(file_path)

        # Read resume text depending on file type
        if resume_file.filename.endswith('.pdf'):
            resume_text = read_pdf(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                resume_text = file.read()

        # Enhanced prompt for AI analysis
        prompt = f"""
        Please analyze the following resume and provide:
        1. A score out of 100.
        2. A list of key strengths, skills, or notable achievements, starting with "Key Points:".

        Resume content:
        {resume_text}
        """
        response = model.generate_content(prompt)
        result_text = clean_text(response.text)

        # Remove <br> tags from result text
        result_text = remove_br_tags(result_text)

        # Extract score
        score_line = next((line for line in result_text.splitlines() if "score" in line.lower()), None)
        if score_line:
            score_match = re.search(r'\d+', score_line)
            score = int(score_match.group()) if score_match else "N/A"

        # Extract key points by finding the "Key Points:" section
        key_points_section = result_text.split("Key Points:", 1)[-1] if "Key Points:" in result_text else ""
        key_points = [point.strip() for point in key_points_section.splitlines() if point.strip()]

        os.remove(file_path)  # Clean up uploaded file

    return render_template('uploadResume.html', score=score, key_points=key_points)


@app.route('/chat')
def chatbot():
    return render_template('chat.html')

@app.route('/get_reply', methods=['POST'])
def get_reply():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"reply": "I didn't receive any message!"}), 400

    # Enhanced prompt for chatbot-like analysis
    prompt = f"""
    Please respond to the following user message with a brief, conversational reply:
    
    User message:
    {user_message}
    """
    response = model.generate_content(prompt)  # Replace with Gemini AI integration

    # Clean and process response text for chatbot
    reply_text = clean_text(response.text)
    reply_text = remove_br_tags(reply_text)

    return jsonify({"reply": reply_text})



@app.route('/')
def index():
    return render_template('login.html')  # Or return a message like "Welcome"


# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True)

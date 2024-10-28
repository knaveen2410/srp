from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from flask_mysqldb import MySQL
from functools import wraps
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config  # Import the Config class
import os  # For handling file paths
from werkzeug.utils import secure_filename  # For secure file uploads
from flask import send_from_directory, abort
from dotenv import load_dotenv
import time
import openai
from openai.error import RateLimitError
import fitz 

RESUME_FOLDER = 'static/resume' 

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.secret_key = 'your_secret_key'  # Secret key for session management

# Set up OpenAI API key
openai.api_key = "sk-svcacct--OL1Empoj__iM-4KLhzf8ngt5BosalsJp-XDvBzsjcfK2ke2xOkoA6V2X4fK-T3BlbkFJLG8kX5QDItMyZNAIsfuQ9b7zTiEa60Zui6J4SryozGa8jcaqsL9x1FlyY4VpgA"
# Load the database configuration from the Config class
app.config.from_object(Config)
 
 
# Initialize MySQL
mysql = MySQL(app)


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
    
    # Fetch job postings
    cur.execute("SELECT * FROM job_postings")  # Make sure to use the correct table name
    job_postings = cur.fetchall()  # Fetch all job postings
    
    cur.close()
    
    return render_template(
        'admin_dashboard.html', 
        total_jobs=total_jobs_count, 
        total_applications=total_applications_count, 
        total_interviews=total_interviews_count, 
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
    
    # Fetch job postings
    cur.execute("SELECT * FROM job_postings")  # Make sure to use the correct table name
    job_postings = cur.fetchall()  # Fetch all job postings
    
    cur.close()
    
    return render_template(
        'hr_dashboard.html', 
        total_jobs=total_jobs_count, 
        total_applications=total_applications_count, 
        total_interviews=total_interviews_count, 
        job_postings=job_postings,  # Pass the job postings to the template
        username=session.get('username'), 
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


# Recruiter dashboard
@app.route('/recruiter-dashboard')
@login_required(roles=["Recruiter"])
def recruiter_dashboard():
    return render_template('recruiter_dashboard.html')

# Interviewer dashboard
@app.route('/interviewer-dashboard')
@login_required(roles=["Interviewer"])
def interviewer_dashboard():
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
    
    return render_template('interviewer_dashboard.html', schedules=schedules)


# Candidate dashboard
@app.route('/candidate-dashboard')
@login_required(roles=["Candidate"])
def candidate_dashboard():
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
        SELECT i.*, a.candidate_id, u.name AS candidate_name 
        FROM interview_schedule i
        JOIN applications a ON i.application_id = a.id
        JOIN users u ON a.candidate_id = u.id
    """)
    upcoming_interviews = cur.fetchall()
    
    cur.close()
    
    return render_template(
        'candidate_dashboard.html',
        job_postings=job_postings,  
        applied_jobs=applied_jobs,
        interviews=upcoming_interviews,  # Pass the list of upcoming interviews to the template
        username=username, 
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


# Route to create a job
@app.route('/create_job', methods=['GET', 'POST'])
@login_required(roles=["HR Manager","Admin"])
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
        return redirect(url_for('hr_dashboard'))

    return render_template('create_job.html')

# Route to edit a job posting (HR Manager only)
@app.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
@login_required(roles=["HR Manager","Admin"])
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

    return redirect(url_for('view_jobs'))




# Route to manage applications 
@app.route('/manage_applications')
@login_required(roles=["HR Manager", "Admin"])
def manage_applications():
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

    return render_template('manage_applications.html', applications=applications)



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
    
    return redirect(url_for('manage_applications'))

@app.route('/reject_application/<int:application_id>', methods=['POST'])
@login_required(roles=["HR Manager","Admin"])
def reject_application(application_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE applications SET status = 'Rejected' WHERE id = %s", (application_id,))
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('manage_applications'))

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


@app.route('/view-applications')
@login_required(roles=["Candidate"])
def view_applications():
    candidate_id = session.get('user_id')  # Ensure you retrieve the candidate ID correctly

    cur = mysql.connection.cursor()
    
    # Fetch applications submitted by the candidate, joining with job_postings to get job titles
    query = """
        SELECT a.*, j.job_title 
        FROM applications a 
        JOIN job_postings j ON a.job_id = j.id 
        WHERE a.candidate_id = %s
    """
    cur.execute(query, (candidate_id,))
    applications = cur.fetchall()

    cur.close()
    
    return render_template('view_applications.html', applications=applications)

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
    if request.method == 'POST':
        interview_date = request.form['interview_date']
        interview_time = request.form['interview_time']
        interviewers = request.form['interviewers']
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO interview_schedule (application_id, interview_date, interview_time, interviewers) VALUES (%s, %s, %s, %s)", 
                    (application_id, interview_date, interview_time, interviewers))
        mysql.connection.commit()
        cur.close()
        
        flash('Interview scheduled successfully!', 'success')
        return redirect(url_for('manage_applications'))

    return render_template('schedule_interview.html', application_id=application_id)



@app.route('/view_interviews')
@login_required(roles=["HR Manager", "Interviewer"])
def view_interviews():
    cur = mysql.connection.cursor()
    
    # Fetch interviews along with candidate names
    cur.execute("""
        SELECT i.*, a.candidate_id, u.name AS candidate_name 
        FROM interview_schedule i
        JOIN applications a ON i.application_id = a.id
        JOIN users u ON a.candidate_id = u.id
    """)
    
    interviews = cur.fetchall()
    cur.close()
    
    return render_template('view_interviews.html', interviews=interviews)



@app.route('/delete_interview/<int:interview_id>', methods=['POST'])
@login_required(roles=["HR Manager", "Admin", "Interviewer"])
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

@app.route('/edit_interview/<int:interview_id>', methods=['GET', 'POST'])
@login_required(roles=["HR Manager", "Interviewer"])
def edit_interview(interview_id):
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        interview_date = request.form['interview_date']
        interview_time = request.form['interview_time']
        interviewers = request.form['interviewers']
        
        cur.execute("""
            UPDATE interview_schedule
            SET interview_date = %s, interview_time = %s, interviewers = %s
            WHERE id = %s
        """, (interview_date, interview_time, interviewers, interview_id))
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('view_interviews'))

    cur.execute("SELECT * FROM interview_schedule WHERE id = %s", (interview_id,))
    interview = cur.fetchone()
    cur.close()
    
    return render_template('edit_interview.html', interview=interview)


@app.route('/generate_reports')
@login_required(roles=["HR Manager", "Admin"])
def generate_reports():
    cur = mysql.connection.cursor()

    # Fetch job postings
    cur.execute("SELECT * FROM job_postings")
    job_postings = cur.fetchall()

    # Fetch applications
    cur.execute("""
        SELECT a.candidate_name, j.job_title, a.status 
        FROM applications a 
        JOIN job_postings j ON a.job_id = j.id
    """)
    applications = cur.fetchall()

    # Fetch interview schedules
    cur.execute("SELECT * FROM interview_schedule")
    interview_schedules = cur.fetchall()

    cur.close()

    return render_template('generate_reports.html', job_postings=job_postings, applications=applications, interview_schedules=interview_schedules)

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
        
        return redirect(url_for('manage_applications'))

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
    cur.execute("SELECT name, username, email FROM users WHERE role='Candidate'")
    candidates = cur.fetchall()
    cur.close()

    return render_template('view_candidates.html', candidates=candidates)




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
        feedback = request.form['feedback']
        rating = request.form['rating']
        name = request.form['name']  # Get the name input
        selection_status = request.form['selection_status']  # Get the selection status input
        
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO interview_feedback (interview_schedule_id, feedback, rating, name, selection_status) 
            VALUES (%s, %s, %s, %s, %s)
        """, (interview_schedule_id, feedback, rating, name, selection_status))
        mysql.connection.commit()
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
        
        return redirect(url_for('manage_applications'))

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




@app.route('/')
def index():
    return render_template('login.html')  # Or return a message like "Welcome"

# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True)

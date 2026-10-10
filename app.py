import os
import re
import math
import uuid
import logging
import functools
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, query_db, execute_db, close_db
from services.recommendations import (
    get_career_profiles,
    get_career_recommendations,
    calculate_placement_readiness,
    calculate_recovery_attendance,
    safe_float
)

# Configure structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("CareerCompass")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_email_format(email):
    """Validates institutional email format."""
    if not email or not EMAIL_REGEX.match(email):
        return False, "Please enter a valid institutional email address (e.g. name@campus.edu)."
    return True, None

def validate_password_policy(password):
    """
    Enforces a balanced password policy:
    - Minimum 8 characters
    - At least 1 letter
    - At least 1 number
    """
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    return True, None

def validate_registration_payload(form):
    """Validates registration input fields and returns dictionary of field errors."""
    errors = {}
    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""
    confirm_password = form.get("confirm_password")
    college = (form.get("college") or "").strip()
    department = (form.get("department") or "").strip()
    year_of_study = form.get("year_of_study")

    # Name
    if not name:
        errors["name"] = "Full name is required."
    elif len(name) < 2:
        errors["name"] = "Full name must be at least 2 characters."

    # Email
    is_valid_email, email_err = validate_email_format(email)
    if not is_valid_email:
        errors["email"] = email_err

    # Password
    is_valid_pwd, pwd_err = validate_password_policy(password)
    if not is_valid_pwd:
        errors["password"] = pwd_err

    # Confirm Password (only enforce mismatch if confirm_password was provided in the submission)
    if confirm_password is not None:
        confirm_pwd_clean = confirm_password.strip()
        if not confirm_pwd_clean:
            errors["confirm_password"] = "Please confirm your password."
        elif password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

    # College
    if "college" in form and not college:
        errors["college"] = "College or university name is required."
    elif college and len(college) < 2:
        errors["college"] = "College name must be at least 2 characters."

    # Department
    if "department" in form and not department:
        errors["department"] = "Course or department is required."

    # Year of Study
    if "year_of_study" in form:
        if not year_of_study or str(year_of_study).strip() == "":
            errors["year_of_study"] = "Please select your year of study (1 to 4)."
        else:
            try:
                y = int(year_of_study)
                if y not in [1, 2, 3, 4]:
                    errors["year_of_study"] = "Please select a valid year of study (1 to 4)."
            except (ValueError, TypeError):
                errors["year_of_study"] = "Year of study must be a valid number (1 to 4)."

    return errors

def create_app(test_config=None):
    app = Flask(__name__)
    
    # Configure application
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "careercompass-dev-secret-key-2026")
    default_db = os.path.join(os.path.dirname(__file__), "database", "careercompass.db")
    app.config["DATABASE"] = os.getenv("DATABASE_PATH", default_db)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    if test_config:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)

    # ---------------------------------------------------------
    # Authentication Gate & Context Decorators
    # ---------------------------------------------------------
    def get_current_student():
        student_id = session.get("student_id")
        if not student_id:
            return None
        try:
            student = query_db("SELECT * FROM students WHERE id = ?", (student_id,), one=True)
            if not student:
                # Clear orphaned session if user was deleted
                session.clear()
                return None
            return student
        except Exception as e:
            logger.error(f"Error resolving current student session {student_id}: {e}", exc_info=True)
            return None

    def login_required(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            student = get_current_student()
            if not student:
                flash("Authentication required. Please sign in to access your student portal.", "warning")
                return redirect(url_for("login"))
            return view(**kwargs)
        return wrapped_view

    @app.context_processor
    def inject_user():
        student = get_current_student()
        return {"current_student": student}

    # ---------------------------------------------------------
    # Public Routes: Landing, Auth & Contact
    # ---------------------------------------------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            data = request.get_json(silent=True) or request.form
            email = (data.get("email") or "").strip().lower()
            password = data.get("password") or ""

            if not email or not password:
                msg = "Please provide both your institutional email and password."
                if request.is_json:
                    return jsonify({"success": False, "error": msg}), 400
                flash(msg, "danger")
                return render_template("login.html", email=email), 400

            try:
                student = query_db("SELECT * FROM students WHERE LOWER(email) = ?", (email,), one=True)
            except Exception as e:
                logger.error(f"Database error during login for {email}: {e}", exc_info=True)
                msg = "A temporary database connection error occurred. Please try again shortly."
                if request.is_json:
                    return jsonify({"success": False, "error": msg}), 500
                flash(msg, "danger")
                return render_template("login.html", email=email), 500

            if student and check_password_hash(student["password_hash"], password):
                session.clear()
                session["student_id"] = student["id"]
                session["student_name"] = student["name"]
                session["student_email"] = student["email"]
                
                flash(f"Welcome back, {student['name']}!", "success")
                if request.is_json:
                    return jsonify({
                        "success": True,
                        "message": "Login successful",
                        "redirect": url_for("dashboard")
                    })
                return redirect(url_for("dashboard"))
            else:
                msg = "Invalid institutional email or password. Please verify your credentials."
                if request.is_json:
                    return jsonify({"success": False, "error": msg}), 401
                flash(msg, "danger")
                return render_template("login.html", email=email)

        return render_template("login.html")

    @app.route("/demo-login/<persona>")
    def demo_login(persona):
        """Instant one-click evaluator login for hackathon demos."""
        persona = persona.lower()
        email = "alex@campus.edu" if persona == "alex" else "priya@campus.edu"
        try:
            student = query_db("SELECT * FROM students WHERE email = ?", (email,), one=True)
        except Exception as e:
            logger.error(f"Error during demo login for {persona}: {e}", exc_info=True)
            student = None
        
        if student:
            session.clear()
            session["student_id"] = student["id"]
            session["student_name"] = student["name"]
            session["student_email"] = student["email"]
            flash(f"⚡ Evaluator Mode: Logged in as demo persona {student['name']}.", "info")
            return redirect(url_for("dashboard"))
        
        flash("Demo student account not found.", "danger")
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            data = request.get_json(silent=True) or request.form

            name = (data.get("name") or "").strip()
            email = (data.get("email") or "").strip().lower()
            password = data.get("password") or ""
            college = (data.get("college") or "Campus Institute of Technology").strip()
            department = (data.get("department") or "Computer Science").strip()
            year_of_study = data.get("year_of_study")
            semester_raw = data.get("semester")
            target_career = (data.get("target_career") or "Full-Stack Web Developer").strip()

            # Determine Year of Study and Semester safely
            if year_of_study:
                try:
                    year_val = int(year_of_study)
                except (ValueError, TypeError):
                    year_val = 3
            elif semester_raw:
                try:
                    year_val = max(1, min(4, (int(semester_raw) + 1) // 2))
                except (ValueError, TypeError):
                    year_val = 3
            else:
                year_val = 3

            # Calculate semester from year of study if not explicitly provided
            if semester_raw:
                try:
                    semester_val = int(semester_raw)
                except (ValueError, TypeError):
                    semester_val = year_val * 2
            else:
                semester_val = year_val * 2

            # Validate input payload
            validation_errors = validate_registration_payload(data)
            if validation_errors:
                first_err = next(iter(validation_errors.values()))
                if request.is_json:
                    return jsonify({
                        "success": False,
                        "errors": validation_errors,
                        "error": first_err
                    }), 400
                flash(first_err, "danger")
                return render_template(
                    "register.html",
                    errors=validation_errors,
                    form_data=data
                ), 400

            # Check for existing email in database
            try:
                existing = query_db("SELECT id FROM students WHERE LOWER(email) = ?", (email,), one=True)
            except Exception as e:
                logger.error(f"Database error during registration email check for {email}: {e}", exc_info=True)
                msg = "A database connectivity issue occurred. Please try again."
                if request.is_json:
                    return jsonify({"success": False, "error": msg}), 500
                flash(msg, "danger")
                return render_template("register.html", errors={"general": msg}, form_data=data), 500

            if existing:
                msg = "An account with this email address already exists. Please sign in or use another email."
                if request.is_json:
                    return jsonify({
                        "success": False,
                        "errors": {"email": "This email address is already registered."},
                        "error": msg
                    }), 409
                flash(msg, "danger")
                return render_template(
                    "register.html",
                    errors={"email": "This email address is already registered."},
                    form_data=data
                ), 409

            # Securely hash password and persist new student record
            pwd_hash = generate_password_hash(password)
            try:
                student_id = execute_db("""
                    INSERT INTO students (name, email, password_hash, college, department, year_of_study, semester, cgpa, target_career)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, email, pwd_hash, college, department, year_val, semester_val, 8.0, target_career))

                # Initialize default placement baseline metrics
                execute_db("""
                    INSERT INTO placement_metrics (student_id, dsa_score, projects_score, aptitude_score)
                    VALUES (?, 65.0, 70.0, 75.0)
                """, (student_id,))

                # Initialize baseline checklist items
                default_checklist = [
                    ("dsa_100_problems", "Solve 100+ LeetCode problems (Array, String, Trees)", "DSA & Algorithms", 0),
                    ("dsa_dp_graphs", "Master Dynamic Programming & Graph Traversal", "DSA & Algorithms", 0),
                    ("project_fullstack", "Build Production Full-Stack Portfolio Web App with CI/CD", "Projects & Portfolio", 0),
                    ("resume_ats_format", "Format ATS-Optimized Single-Page Tech Resume", "Resume & Credentials", 0),
                    ("aptitude_mock_tests", "Complete 10 Quantitative, Verbal & Logical Tests", "Aptitude & Tests", 0),
                    ("behavioral_pitch", "Record 2-Minute STAR Behavioral Elevator Pitches", "Mock Interviews", 0),
                    ("system_design_basics", "Architect Caching, Load Balancers & Database Sharding", "System Design", 0)
                ]
                for key, title, cat, done in default_checklist:
                    execute_db("""
                        INSERT INTO placement_checklist (student_id, item_key, title, category, is_completed)
                        VALUES (?, ?, ?, ?, ?)
                    """, (student_id, key, title, cat, done))

                # Initialize baseline semester GPAs for completed semesters
                for sem_idx in range(1, max(2, semester_val)):
                    execute_db("INSERT OR IGNORE INTO semester_gpa (student_id, semester, gpa) VALUES (?, ?, 8.0)", (student_id, sem_idx))

                # Seed default starter attendance subjects
                starter_subjects = [
                    ("CS601", "Core Software Engineering", 32, 40),
                    ("CS602", "Relational Database Systems", 35, 40),
                    ("CS603", "Data Communication & Networks", 30, 40)
                ]
                for code, sname, att, tot in starter_subjects:
                    execute_db("""
                        INSERT INTO attendance (student_id, subject_code, subject_name, attended_classes, total_classes)
                        VALUES (?, ?, ?, ?, ?)
                    """, (student_id, code, sname, att, tot))

                # Establish authenticated session
                session.clear()
                session["student_id"] = student_id
                session["student_name"] = name
                session["student_email"] = email

                success_msg = f"Registration successful! Welcome to CareerCompass AI, {name}."
                flash(success_msg, "success")

                if request.is_json:
                    return jsonify({
                        "success": True,
                        "message": success_msg,
                        "redirect": url_for("dashboard")
                    }), 201

                return redirect(url_for("dashboard"))

            except Exception as e:
                logger.error(f"Error persisting new student {email}: {e}", exc_info=True)
                err_msg = "An unexpected error occurred while creating your profile. Please try again."
                if request.is_json:
                    return jsonify({"success": False, "error": err_msg}), 500
                flash(err_msg, "danger")
                return render_template("register.html", errors={"general": err_msg}, form_data=data), 500

        return render_template("register.html")

    @app.route("/logout", methods=["GET", "POST"])
    def logout():
        session.clear()
        flash("You have been signed out successfully.", "info")
        return redirect(url_for("login"))

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip()
            subject = (request.form.get("subject") or "").strip()
            message = (request.form.get("message") or "").strip()

            if not name or not email or not message or not subject:
                flash("Please complete all required fields.", "danger")
                return render_template("contact.html", form_data=request.form), 400

            is_valid_email, email_err = validate_email_format(email)
            if not is_valid_email:
                flash(email_err, "danger")
                return render_template("contact.html", form_data=request.form), 400

            try:
                execute_db("""
                    INSERT INTO contact_messages (name, email, subject, message)
                    VALUES (?, ?, ?, ?)
                """, (name, email, subject, message))
                flash("Thank you! Your inquiry has been submitted to the Campus Career Advisory Cell.", "success")
                return redirect(url_for("contact"))
            except Exception as e:
                logger.error(f"Database error saving contact inquiry: {e}", exc_info=True)
                flash("A temporary database issue occurred while sending your inquiry. Please try again.", "danger")
                return render_template("contact.html", form_data=request.form), 500

        return render_template("contact.html")

    # ---------------------------------------------------------
    # Core Student Portal Routes (Authenticated)
    # ---------------------------------------------------------
    @app.route("/dashboard")
    @login_required
    def dashboard():
        student = get_current_student()
        if not student:
            return redirect(url_for("login"))
        student_id = student["id"]

        try:
            # 1. Attendance Metrics & Alert Banners
            attendance_rows = query_db("SELECT * FROM attendance WHERE student_id = ?", (student_id,)) or []
            total_att = sum(r["attended_classes"] for r in attendance_rows)
            total_cls = sum(r["total_classes"] for r in attendance_rows)
            overall_attendance_pct = round((total_att / total_cls) * 100.0, 1) if total_cls > 0 else 0.0

            # Check for subjects < 75%
            critical_subjects = []
            for r in attendance_rows:
                pct = (r["attended_classes"] / r["total_classes"] * 100.0) if r["total_classes"] > 0 else 0.0
                if pct < 75.0:
                    critical_subjects.append({
                        "code": r["subject_code"],
                        "name": r["subject_name"],
                        "pct": round(pct, 1)
                    })

            # 2. Academic Coursework Performance
            marks_rows = query_db("SELECT * FROM academic_records WHERE student_id = ?", (student_id,)) or []
            avg_marks = round(sum(r["total_marks"] for r in marks_rows) / len(marks_rows), 1) if marks_rows else 0.0

            # 3. Placement Readiness
            metrics = query_db("SELECT * FROM placement_metrics WHERE student_id = ?", (student_id,), one=True)
            dsa = metrics["dsa_score"] if metrics else 70.0
            proj = metrics["projects_score"] if metrics else 75.0
            apt = metrics["aptitude_score"] if metrics else 80.0
            readiness_score = calculate_placement_readiness(dsa, student["cgpa"], proj, apt, overall_attendance_pct)

            # 4. Placement Checklist Progress
            checklist_rows = query_db("SELECT * FROM placement_checklist WHERE student_id = ?", (student_id,)) or []
            done_count = sum(1 for c in checklist_rows if c["is_completed"])
            checklist_total = len(checklist_rows)
            checklist_pct = round((done_count / checklist_total) * 100.0, 1) if checklist_total > 0 else 0.0

            # 5. Top Career Recommendation Preview
            skills_rows = query_db("SELECT skill_name FROM student_skills WHERE student_id = ?", (student_id,)) or []
            skills = [s["skill_name"] for s in skills_rows]
            recommendations = get_career_recommendations(student, skills, marks_rows, overall_attendance_pct)
            top_career = recommendations[0] if recommendations else None

            return render_template(
                "dashboard.html",
                student=student,
                overall_attendance_pct=overall_attendance_pct,
                critical_subjects=critical_subjects,
                avg_marks=avg_marks,
                readiness_score=readiness_score,
                checklist_pct=checklist_pct,
                checklist_done=done_count,
                checklist_total=checklist_total,
                top_career=top_career,
                marks_rows=marks_rows
            )
        except Exception as e:
            logger.error(f"Error rendering dashboard for student {student_id}: {e}", exc_info=True)
            flash("Error loading dashboard metrics. A safe recovery view has been initialized.", "warning")
            return render_template(
                "dashboard.html",
                student=student,
                overall_attendance_pct=0.0,
                critical_subjects=[],
                avg_marks=0.0,
                readiness_score=70.0,
                checklist_pct=0.0,
                checklist_done=0,
                checklist_total=0,
                top_career=None,
                marks_rows=[]
            )

    @app.route("/attendance")
    @login_required
    def attendance():
        student = get_current_student()
        if not student:
            return redirect(url_for("login"))
        student_id = student["id"]
        rows = query_db("SELECT * FROM attendance WHERE student_id = ?", (student_id,)) or []

        attendance_list = []
        total_att = 0
        total_cls = 0

        for r in rows:
            att = r["attended_classes"]
            tot = r["total_classes"]
            total_att += att
            total_cls += tot
            pct = round((att / tot) * 100.0, 1) if tot > 0 else 0.0
            
            # Badge status
            if pct >= 80.0:
                badge = "safe"
            elif pct >= 75.0:
                badge = "warning"
            else:
                badge = "critical"

            # Precalculate recovery metrics for institutional thresholds
            rec_75 = calculate_recovery_attendance(att, tot, 0.75)
            rec_80 = calculate_recovery_attendance(att, tot, 0.80)

            attendance_list.append({
                "id": r["id"],
                "subject_code": r["subject_code"],
                "subject_name": r["subject_name"],
                "attended": att,
                "total": tot,
                "percentage": pct,
                "badge": badge,
                "rec_75": rec_75,
                "rec_80": rec_80
            })

        overall_pct = round((total_att / total_cls) * 100.0, 1) if total_cls > 0 else 0.0
        rec_overall_75 = calculate_recovery_attendance(total_att, total_cls, 0.75)

        return render_template(
            "attendance.html",
            student=student,
            attendance_list=attendance_list,
            overall_pct=overall_pct,
            rec_overall_75=rec_overall_75,
            total_att=total_att,
            total_cls=total_cls
        )

    @app.route("/attendance/log", methods=["POST"])
    @app.route("/api/attendance/log", methods=["POST"])
    @login_required
    def log_attendance():
        """Logs an attended lecture for a subject with instant persistence."""
        student_id = session["student_id"]
        data = request.get_json(silent=True) or request.form
        subject_code = data.get("subject_code")

        if not subject_code:
            if request.is_json:
                return jsonify({"success": False, "error": "Subject code required"}), 400
            flash("Subject code required to log lecture.", "danger")
            return redirect(url_for("attendance"))

        record = query_db("""
            SELECT * FROM attendance WHERE student_id = ? AND subject_code = ?
        """, (student_id, subject_code), one=True)

        if not record:
            if request.is_json:
                return jsonify({"success": False, "error": "Subject not found"}), 404
            flash(f"Subject {subject_code} not found.", "danger")
            return redirect(url_for("attendance"))

        new_att = record["attended_classes"] + 1
        new_tot = record["total_classes"] + 1
        new_pct = round((new_att / new_tot) * 100.0, 1)

        execute_db("""
            UPDATE attendance
            SET attended_classes = ?, total_classes = ?
            WHERE student_id = ? AND subject_code = ?
        """, (new_att, new_tot, student_id, subject_code))

        if request.is_json:
            return jsonify({
                "success": True,
                "subject_code": subject_code,
                "attended": new_att,
                "total": new_tot,
                "percentage": new_pct
            })

        flash(f"Logged lecture attendance for {record['subject_name']}. New attendance: {new_pct}%.", "success")
        return redirect(url_for("attendance"))

    @app.route("/analytics")
    @login_required
    def analytics():
        student = get_current_student()
        if not student:
            return redirect(url_for("login"))
        student_id = student["id"]

        marks_rows = query_db("SELECT * FROM academic_records WHERE student_id = ?", (student_id,)) or []
        strengths = [m for m in marks_rows if m["total_marks"] >= 80.0]
        practice_areas = [m for m in marks_rows if m["total_marks"] < 75.0]

        gpa_rows = query_db("SELECT * FROM semester_gpa WHERE student_id = ? ORDER BY semester ASC", (student_id,)) or []

        return render_template(
            "analytics.html",
            student=student,
            marks_rows=marks_rows,
            strengths=strengths,
            practice_areas=practice_areas,
            gpa_rows=gpa_rows
        )

    @app.route("/career-ai")
    @login_required
    def career_ai():
        student = get_current_student()
        if not student:
            return redirect(url_for("login"))
        student_id = student["id"]

        skills_rows = query_db("SELECT * FROM student_skills WHERE student_id = ?", (student_id,)) or []
        skills = [s["skill_name"] for s in skills_rows]
        marks_rows = query_db("SELECT * FROM academic_records WHERE student_id = ?", (student_id,)) or []

        attendance_rows = query_db("SELECT * FROM attendance WHERE student_id = ?", (student_id,)) or []
        total_att = sum(r["attended_classes"] for r in attendance_rows)
        total_cls = sum(r["total_classes"] for r in attendance_rows)
        overall_attendance_pct = round((total_att / total_cls) * 100.0, 1) if total_cls > 0 else 0.0

        recommendations = get_career_recommendations(student, skills, marks_rows, overall_attendance_pct)
        all_profiles = get_career_profiles()

        return render_template(
            "career_ai.html",
            student=student,
            skills_rows=skills_rows,
            recommendations=recommendations,
            all_profiles=all_profiles
        )

    @app.route("/career-preferences", methods=["POST"])
    @app.route("/api/career-preferences", methods=["POST"])
    @login_required
    def update_career_preferences():
        student_id = session["student_id"]
        data = request.get_json(silent=True) or request.form
        target_career = data.get("target_career", "").strip()

        if target_career:
            execute_db("UPDATE students SET target_career = ? WHERE id = ?", (target_career, student_id))
            if request.is_json:
                return jsonify({"success": True, "target_career": target_career})
            flash(f"Career focus updated to {target_career}.", "success")
        else:
            if request.is_json:
                return jsonify({"success": False, "error": "Target career required"}), 400
            flash("Target career cannot be empty.", "warning")

        return redirect(url_for("career_ai"))

    @app.route("/skills/add", methods=["POST"])
    @app.route("/api/skills/add", methods=["POST"])
    @login_required
    def add_skill():
        student_id = session["student_id"]
        data = request.get_json(silent=True) or request.form
        skill_name = (data.get("skill_name") or "").strip()
        proficiency = (data.get("proficiency") or "Intermediate").strip()

        if not skill_name:
            if request.is_json:
                return jsonify({"success": False, "error": "Skill name required"}), 400
            flash("Skill name required.", "danger")
            return redirect(url_for("career_ai"))

        try:
            execute_db("""
                INSERT INTO student_skills (student_id, skill_name, proficiency)
                VALUES (?, ?, ?)
            """, (student_id, skill_name, proficiency))
            msg = f"Added '{skill_name}' to your skill profile."
            if request.is_json:
                return jsonify({"success": True, "skill_name": skill_name, "proficiency": proficiency})
            flash(msg, "success")
        except Exception:
            if request.is_json:
                return jsonify({"success": False, "error": "Skill already in profile"}), 409
            flash(f"Skill '{skill_name}' is already in your profile.", "warning")

        return redirect(url_for("career_ai"))

    @app.route("/skills/remove", methods=["POST"])
    @app.route("/api/skills/remove", methods=["POST"])
    @login_required
    def remove_skill():
        student_id = session["student_id"]
        data = request.get_json(silent=True) or request.form
        skill_name = (data.get("skill_name") or "").strip()
        skill_id = data.get("skill_id")

        if skill_id:
            execute_db("DELETE FROM student_skills WHERE id = ? AND student_id = ?", (skill_id, student_id))
        elif skill_name:
            execute_db("DELETE FROM student_skills WHERE student_id = ? AND LOWER(skill_name) = ?", (student_id, skill_name.lower()))
        else:
            if request.is_json:
                return jsonify({"success": False, "error": "Skill identifier required"}), 400
            flash("Skill identifier required.", "danger")
            return redirect(url_for("career_ai"))

        if request.is_json:
            return jsonify({"success": True, "removed": skill_name or skill_id})

        flash("Removed skill from your profile.", "info")
        return redirect(url_for("career_ai"))

    @app.route("/placement")
    @login_required
    def placement():
        student = get_current_student()
        if not student:
            return redirect(url_for("login"))
        student_id = student["id"]

        metrics = query_db("SELECT * FROM placement_metrics WHERE student_id = ?", (student_id,), one=True)
        dsa = metrics["dsa_score"] if metrics else 70.0
        proj = metrics["projects_score"] if metrics else 75.0
        apt = metrics["aptitude_score"] if metrics else 80.0

        attendance_rows = query_db("SELECT * FROM attendance WHERE student_id = ?", (student_id,)) or []
        total_att = sum(r["attended_classes"] for r in attendance_rows)
        total_cls = sum(r["total_classes"] for r in attendance_rows)
        att_pct = round((total_att / total_cls) * 100.0, 1) if total_cls > 0 else 0.0

        readiness_score = calculate_placement_readiness(dsa, student["cgpa"], proj, apt, att_pct)

        checklist_rows = query_db("""
            SELECT * FROM placement_checklist WHERE student_id = ? ORDER BY id ASC
        """, (student_id,)) or []

        pending_items = [c for c in checklist_rows if not c["is_completed"]]
        actionable_steps = [item["title"] for item in pending_items[:4]]

        return render_template(
            "placement.html",
            student=student,
            metrics=metrics or {"dsa_score": dsa, "projects_score": proj, "aptitude_score": apt},
            overall_attendance_pct=att_pct,
            readiness_score=readiness_score,
            checklist=checklist_rows,
            actionable_steps=actionable_steps
        )

    @app.route("/api/toggle-checklist-item", methods=["POST"])
    @login_required
    def toggle_checklist_item():
        """Interactive Live Checklist AJAX endpoint."""
        student_id = session["student_id"]
        data = request.get_json(silent=True) or request.form
        item_id = data.get("item_id")
        item_key = data.get("item_key")

        if item_id:
            item = query_db("SELECT * FROM placement_checklist WHERE id = ? AND student_id = ?", (item_id, student_id), one=True)
        elif item_key:
            item = query_db("SELECT * FROM placement_checklist WHERE item_key = ? AND student_id = ?", (item_key, student_id), one=True)
        else:
            return jsonify({"success": False, "error": "Item identifier missing"}), 400

        if not item:
            return jsonify({"success": False, "error": "Checklist item not found"}), 404

        new_status = 0 if item["is_completed"] else 1
        execute_db("UPDATE placement_checklist SET is_completed = ? WHERE id = ?", (new_status, item["id"]))

        # Recalculate composite readiness score
        student = get_current_student()
        metrics = query_db("SELECT * FROM placement_metrics WHERE student_id = ?", (student_id,), one=True)
        dsa = metrics["dsa_score"] if metrics else 70.0
        proj = metrics["projects_score"] if metrics else 75.0
        apt = metrics["aptitude_score"] if metrics else 80.0

        att_rows = query_db("SELECT * FROM attendance WHERE student_id = ?", (student_id,)) or []
        total_att = sum(r["attended_classes"] for r in att_rows)
        total_cls = sum(r["total_classes"] for r in att_rows)
        att_pct = round((total_att / total_cls) * 100.0, 1) if total_cls > 0 else 0.0

        base_readiness = calculate_placement_readiness(dsa, student["cgpa"], proj, apt, att_pct)
        all_items = query_db("SELECT is_completed FROM placement_checklist WHERE student_id = ?", (student_id,)) or []
        comp_count = sum(1 for i in all_items if i["is_completed"])
        total_count = len(all_items)
        completion_ratio = (comp_count / total_count) if total_count > 0 else 0.0

        return jsonify({
            "success": True,
            "item_id": item["id"],
            "item_key": item["item_key"],
            "is_completed": bool(new_status),
            "completed_count": comp_count,
            "total_count": total_count,
            "completion_ratio": round(completion_ratio * 100.0, 1),
            "new_readiness_score": base_readiness
        })

    @app.route("/placement/metrics", methods=["POST"])
    @app.route("/api/placement-metrics", methods=["POST"])
    @login_required
    def update_placement_metrics():
        student_id = session["student_id"]
        data = request.get_json(silent=True) or request.form

        try:
            dsa = float(data.get("dsa_score", 70.0))
            proj = float(data.get("projects_score", 75.0))
            apt = float(data.get("aptitude_score", 80.0))
        except (ValueError, TypeError):
            if request.is_json:
                return jsonify({"success": False, "error": "Invalid metric numbers"}), 400
            flash("Invalid numeric metrics supplied.", "danger")
            return redirect(url_for("placement"))

        execute_db("""
            INSERT INTO placement_metrics (student_id, dsa_score, projects_score, aptitude_score)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                dsa_score = excluded.dsa_score,
                projects_score = excluded.projects_score,
                aptitude_score = excluded.aptitude_score
        """, (student_id, dsa, proj, apt))

        student = get_current_student()
        att_rows = query_db("SELECT * FROM attendance WHERE student_id = ?", (student_id,)) or []
        total_att = sum(r["attended_classes"] for r in att_rows)
        total_cls = sum(r["total_classes"] for r in att_rows)
        att_pct = round((total_att / total_cls) * 100.0, 1) if total_cls > 0 else 0.0

        new_score = calculate_placement_readiness(dsa, student["cgpa"], proj, apt, att_pct)

        if request.is_json:
            return jsonify({
                "success": True,
                "dsa_score": dsa,
                "projects_score": proj,
                "aptitude_score": apt,
                "new_readiness_score": new_score
            })

        flash("Placement preparation metrics updated successfully.", "success")
        return redirect(url_for("placement"))

    # ---------------------------------------------------------
    # Error Handlers
    # ---------------------------------------------------------
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        incident_id = f"CC-{uuid.uuid4().hex[:8].upper()}"
        logger.error(f"Internal Server Error [Incident {incident_id}]: {e}", exc_info=True)
        return render_template("500.html", incident_id=incident_id), 500

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

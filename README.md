# CareerCompass AI (Campus-career AI) 🧭

> **Intelligent Academic & Career Guidance Platform for Modern Campus Engineers**  
> *Deterministic Heuristic Rule-Based Intelligence Engine with Zero Black-Box Hallucination*  
> 
> 🌐 **Live Production URL:** [https://campus-career-ai-psi.vercel.app](https://campus-career-ai-psi.vercel.app)

---

## 🌟 Executive Summary

**CareerCompass AI** is a full-stack campus intelligence and career telemetry platform designed for engineering institutions. It provides transparent, mathematically rigorous tools to bridge the gap between classroom academics and corporate placement readiness.

Unlike unpredictable black-box LLM systems, CareerCompass AI uses an **explainable multi-factor heuristic intelligence engine** to compute career match scores, attendance recovery trajectories, and placement readiness composites with 100% auditability and data isolation.

---

## 🏗️ Architecture & Project Structure

```text
Campus-career AI/
├── app.py                     # Main Flask web application, routing, auth & REST APIs
├── requirements.txt           # Production dependencies (Flask, Werkzeug, Pytest, Gunicorn)
├── .env.example               # Template environment configuration
├── .env                       # Local environment variables
├── README.md                  # Comprehensive setup, architecture & deployment documentation
│
├── database/
│   ├── db.py                  # SQLite connection helper, parameterization & query wrapper
│   ├── init_db.py             # Schema initialization and rich demo student seeding
│   ├── schema.sql             # Relational SQLite tables DDL
│   └── careercompass.db       # SQLite database file
│
├── services/
│   └── recommendations.py     # Deterministic Heuristic AI engine, gap analysis & readiness math
│
├── templates/
│   ├── base.html              # Responsive dark navy shell with sidebar navigation
│   ├── index.html             # Landing page with hero, live preview telemetry & feature grid
│   ├── login.html             # Secure login & one-click hackathon demo persona buttons
│   ├── register.html          # Student account registration with department selection
│   ├── dashboard.html         # Overview dashboard with KPI cards & Chart.js preview
│   ├── attendance.html        # Subject-wise attendance matrix & What-If simulator
│   ├── analytics.html         # Performance charts (marks vs class avg, GPA line trajectory)
│   ├── career_ai.html         # CareerCompass AI matching, skill gaps & 4-phase roadmaps
│   ├── placement.html         # Placement readiness formula & interactive AJAX checklist
│   ├── contact.html           # Advisory cell inquiry form with database persistence
│   ├── 404.html               # Custom 404 error page
│   └── 500.html               # Custom 500 error page
│
├── static/
│   ├── css/
│   │   └── style.css          # Dark navy design system, cyan/purple glowing accents & glassmorphism
│   ├── js/
│   │   └── script.js          # Chart.js configs, AJAX checklist toggling & recovery calculator
│   └── images/                # Static asset directory
│
└── tests/
    ├── test_app.py            # Route, authentication, isolation & AJAX tests (14 tests)
    └── test_recommendations.py# Recommendation engine, gap analysis & math formula tests (5 tests)
```

---

## 🚀 Key Features Implemented

### 1. 🌟 Executive Dashboard (`/dashboard`)
- **Key Metric KPI Cards**: Overall Attendance %, Average Marks & GPA (10-point scale), Assignment/Checklist completion progress, and Composite Placement Readiness Score.
- **Visual Alert Banners**: Automatically alerts students if any subject is below the **75% institutional threshold** (e.g. Computer Networks at 71.4%).
- **Chart.js Comparison**: Comparative bar chart displaying student marks against class benchmarks.
- **Top Career Recommendation Card**: Dynamic preview with match percentage, description, and missing skills.

### 2. 📅 Subject-Wise Attendance & "What-If" Simulator (`/attendance`)
- **Subject Attendance Matrix**: Color-coded badges: Safe ($\ge 80\%$), Warning ($75\% - 79.9\%$), and Critical Attention ($< 75\%$).
- **Interactive Log Button**: Allows students to log an attended lecture with immediate database persistence.
- **Recovery Simulator**:
  - Computes the exact number of consecutive classes a student must attend without absence to reach $75\%$ or $80\%$.
  - Computes the safe absence margin a student can miss while remaining compliant.
  - Interactive live simulation slider/inputs.

### 3. 📈 Academic Performance Analytics (`/analytics`)
- **Interactive Visualizations**:
  - **Bar Chart**: Coursework marks vs. class average per subject.
  - **Line Chart**: Multi-semester cumulative GPA trajectory across Semesters 1 to 5.
- **Strengths Identification**: Automatically highlights subjects with marks $\ge 80\%$ and explains positive factors.
- **Targeted Practice Areas**: Diagnoses subjects $< 75\%$ with suggested study schedules.
- **Comprehensive examination breakdown table**: Internal assessment (30M) vs. end-semester exam (70M).

### 4. 🧭 CareerCompass AI — Unique Feature (`/career-ai`)
- **Multi-Role Profiling**:
  1. Full-Stack Web Developer
  2. Data Analyst / BI Specialist
  3. AI & Machine Learning Engineer
  4. Software Development Engineer (SDE / Systems)
- **Transparent Match Score (0–100%)**:
  $$\text{Match Score} = (\text{Skill Overlap} \times 45\%) + (\text{Academic Coursework} \times 25\%) + (\text{Declared Interests} \times 20\%) + (\text{Attendance} \times 10\%)$$
- **Explainable "Why This Matches You"**: Cites specific coursework scores and matching competencies.
- **Skill Gap Radar**: Separates Matched Skills (green pills) from Missing Skills to Acquire (red pills).
- **Personalized 4-Phase Learning Roadmaps**: Week-by-week curriculum (Foundations $\to$ Core Tools $\to$ Advanced Specialization $\to$ Cloud & Deployment).
- **Curated Project Ideas**: Practical portfolio projects with recommended technology stacks.
- **Transparent Engine Disclosure**: Explicitly labeled as a deterministic, explainable Heuristic Rule-Based Intelligence Engine with zero black-box hallucination.
- **Profile Customization**: Students dynamically add/remove skills and update career goals, recalculating recommendations in real time.

### 5. 🎯 Placement Readiness Engine (`/placement`)
- **Transparent 5-Factor Mathematical Model**:
  $$\text{Readiness Score} = \text{Technical/DSA (35\%)} + \text{Academic GPA (20\%)} + \text{Projects/Resume (20\%)} + \text{Aptitude/Mock (15\%)} + \text{Attendance Reliability (10\% variance)}$$
- **Interactive Live Checklist (AJAX)**: Checkboxes for DSA milestones, ATS resume formatting, quantitative tests, and behavioral pitches sync with `/api/toggle-checklist-item` and update the composite readiness score without page reload.
- **Actionable Next Steps**: Prioritized list of concrete preparation actions.

### 6. 🔐 Authentication & Security (`/login`, `/register`)
- Session-based authentication with `werkzeug.security` password hashing (`scrypt`/`pbkdf2`).
- Parameterized SQL queries preventing SQL injection.
- Complete user isolation (students only view and modify their own records).
- **One-Click Hackathon Evaluator Access**:
  - **Alex Mercer** (`alex@campus.edu` / `password123`): Computer Science (Full-Stack & SDE track)
  - **Priya Sharma** (`priya@campus.edu` / `password123`): AI & Data Science (Machine Learning track)

### 7. 📬 Campus Advisory Support (`/contact`)
- Validated contact form storing inquiries directly into the SQLite `contact_messages` table.
- Feedback confirmation flash messages and campus advisory cell office hours.

---

## 🧮 Mathematical Formulas & Reasoning

### 1. Career Match Score Formula
$$\text{Match Score} = (0.45 \times S) + (0.25 \times A) + (0.20 \times I) + (0.10 \times C)$$
Where:
- $S$: Skill Overlap percentage ($0 - 100\%$)
- $A$: Academic Coursework affinity score ($0 - 100\%$)
- $I$: Declared Interests / Track alignment ($0 - 100\%$)
- $C$: Overall Attendance compliance percentage ($0 - 100\%$)

### 2. Placement Readiness Composite Formula
$$\text{Readiness Score} = (0.35 \times \text{DSA}) + (0.20 \times [\text{CGPA} \times 10]) + (0.20 \times \text{Projects}) + (0.15 \times \text{Aptitude}) + (0.10 \times \text{Attendance})$$

### 3. Attendance Recovery Equation
To attain threshold $P$ ($0.75$ or $0.80$) with current attended $A$ and total classes $T$:
$$\frac{A + C}{T + C} \ge P \implies C \ge \left\lceil \frac{P \cdot T - A}{1 - P} \right\rceil$$

Safe absence margin $M$ while remaining $\ge P$:
$$\frac{A}{T + M} \ge P \implies M \le \left\lfloor \frac{A - P \cdot T}{P} \right\rfloor$$

---

## 🧪 Automated Testing Verification

The test suite contains **19 comprehensive unit and integration tests** covering all routes, authentication gates, data isolation, AJAX updates, and recommendation math.

Run tests:
```powershell
python -m pytest tests/ -v
```

Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.15.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\astikartha\Downloads\New folder
collected 19 items

tests/test_app.py::test_home_page PASSED                                 [  5%]
tests/test_app.py::test_login_page_renders PASSED                        [ 10%]
tests/test_app.py::test_login_invalid_credentials PASSED                 [ 15%]
tests/test_app.py::test_demo_login_alex PASSED                           [ 21%]
tests/test_app.py::test_protected_routes_require_login PASSED            [ 26%]
tests/test_app.py::test_authenticated_dashboard_flow PASSED              [ 31%]
tests/test_app.py::test_contact_form_submission PASSED                   [ 36%]
tests/test_app.py::test_ajax_checklist_toggle PASSED                     [ 42%]
tests/test_app.py::test_student_registration PASSED                      [ 47%]
tests/test_app.py::test_skill_management PASSED                          [ 52%]
tests/test_app.py::test_career_preferences_update PASSED                 [ 57%]
tests/test_app.py::test_attendance_logging PASSED                        [ 63%]
tests/test_app.py::test_placement_metrics_update PASSED                  [ 68%]
tests/test_app.py::test_logout PASSED                                    [ 73%]
tests/test_recommendations.py::test_career_profiles_exist PASSED         [ 78%]
tests/test_recommendations.py::test_skill_overlap_detection PASSED       [ 84%]
tests/test_recommendations.py::test_academic_affinity_calculation PASSED [ 89%]
tests/test_recommendations.py::test_career_recommendations_structure PASSED [ 94%]
tests/test_recommendations.py::test_placement_readiness_formula PASSED   [100%]

============================= 19 passed in 4.46s ==============================
```

---

## 💻 How to Run Locally

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Initialize Database (Already Seeded)
```powershell
python database/init_db.py
```

### Step 3: Start the Application
```powershell
python app.py
```

Open your browser at:
**`http://127.0.0.1:5000`**

Click **"⚡ Explore Live Demo"** on the landing page or login with:
- `alex@campus.edu` / `password123`
- `priya@campus.edu` / `password123`

---

## 🌐 Deployment Instructions (Obtaining a Public URL)

### Option A: Render.com (Recommended Free Hosting)
1. Initialize repository and commit:
   ```bash
   git init
   git add .
   git commit -m "feat: complete CareerCompass AI platform"
   git remote add origin https://github.com/<your-username>/careercompass-ai.git
   git push -u origin main
   ```
2. On Render.com, create a **New + Web Service** and connect your repository.
3. Configure settings:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && python database/init_db.py`
   - **Start Command**: `gunicorn app:app`
4. Set Environment Variables:
   - `SECRET_KEY`: `<any-secure-random-string>`
   - `FLASK_ENV`: `production`

### Option B: Instant Local Tunneling for Hackathon Judging (ngrok)
In terminal 1:
```powershell
python app.py
```

In terminal 2:
```powershell
npx ngrok http 5000
```
ngrok will provide an instant HTTPS URL (e.g., `https://xxxx.ngrok-free.app`) accessible from any judge's smartphone or laptop.

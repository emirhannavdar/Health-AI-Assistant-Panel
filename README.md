# Health AI Assistant Panel

## Project Overview

This project is a modern, secure, and feature-rich health assistant panel designed for clinics, hospitals, or personal health management. It integrates advanced AI (Google Gemini) for lab result analysis, personalized health advice, and clinical decision support. The system supports multiple user roles (Admin, Doctor, Patient) with robust authentication and authorization mechanisms.

## Features

- **AI-Powered Lab Result Analysis:** Automatic interpretation and risk assessment of lab results using Gemini AI.
- **Role-Based Access:** Separate interfaces and permissions for Admin, Doctor, and Patient users.
- **Admin Panel:** Manage doctors, reset passwords, and reassign patients securely.
- **Doctor Panel:** Enter lab results, view and manage patient results, and access AI-powered tools.
- **Patient Panel:** View personal lab results and receive AI-generated health advice.
- **AI Q&A:** Ask health-related questions to the AI and receive instant answers.
- **Report Upload & Explanation:** Upload medical documents and get AI-generated explanations.
- **Symptom Analysis:** Enter symptoms and receive AI-driven analysis.
- **Clinical Decision Support:** Doctors can get AI suggestions based on patient history and lab data.
- **Modern UI/UX:** Responsive, user-friendly interface with dynamic menus and modals.
- **Security:** JWT-based authentication, password hashing, and role-based access control.

## Technologies Used

- **Backend:** Python (FastAPI), SQLAlchemy, Alembic
- **Frontend:** HTML5, Bootstrap 5, Vanilla JavaScript
- **AI Integration:** Google Gemini API
- **Database:** SQLite (default, can be changed)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/health-ai-panel.git
   cd health-ai-panel
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```
4. **Start the backend server:**
   ```bash
   python main.py
   ```
5. **(Optional) Start the reference API (for lab units/ranges):**
   ```bash
   python reference_api/reference_api.py
   ```
6. **Access the panel:**
   Open your browser and go to `http://localhost:8000`

## Usage

- **Login:** Choose your role (Patient or Doctor) and log in with your credentials.
- **Admin Access:** Only users with admin privileges can access the admin panel.
- **Lab Results:** Doctors can enter and analyze lab results; patients can view their results.
- **AI Tools:** Use the AI Q&A, report upload, symptom analysis, and clinical decision support features as needed.

## Security

- **Authentication:** JWT tokens are used for secure API access.
- **Authorization:** Role-based access ensures only authorized users can access sensitive features.
- **Password Storage:** All passwords are securely hashed.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

**Note:**
- For production use, configure environment variables and use a production-ready database and server.
- The Gemini AI integration requires a valid API key.

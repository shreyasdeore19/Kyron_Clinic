# Kyron Medical — AI Patient Assistant

A cutting-edge web application for **Kyron Medical** that provides patients with an intelligent, human-like AI chat interface for appointment scheduling, prescription refills, and practice information — with seamless voice call handoff.

## Features

### Core
- **AI Chat Interface** — Conversational AI assistant ("Kyra") powered by Google Gemini
- **Patient Intake** — Collects first/last name, DOB, phone, email, and reason for visit
- **Semantic Doctor Matching** — Matches patient symptoms to the right specialist (5 doctors across orthopedics, cardiology, gastroenterology, neurology, dermatology)
- **Appointment Scheduling** — 30-60 days of hard-coded availability with date/time slot selection and preference filtering ("Do you have Tuesdays?", "I need a morning slot")
- **Email Confirmation** — Sends styled HTML confirmation email upon booking

### Voice AI
- **Chat-to-Voice Handoff** — One-click button transfers the conversation to a phone call via Vapi.ai, retaining full chat context
- **Context Summary** — AI generates a conversation summary passed to the voice agent for seamless continuation

### Additional Workflows
- **Prescription Refill** — Identity verification + simulated refill request forwarding
- **Office Hours & Address** — Instant practice information retrieval
- **SMS Opt-in** — Post-appointment SMS notification opt-in modal

### UI/UX
- **Liquid Glass Design** — Frosted glass panels with backdrop blur, translucency, and depth
- **Kyron Medical Branding** — Cyan-to-purple gradient accent, dark theme
- **Smooth Animations** — Spring-based message entrance, typing indicators, floating orbs, pulse effects
- **Responsive** — Works on desktop and mobile

## Quick Start

### 1. Clone & Setup
```bash
cd ~/kyron_clinic
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Edit the `.env` file in the project root:

```env
GEMINI_API_KEY=your_actual_gemini_api_key
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
VAPI_API_KEY=your_vapi_key           # Optional — for voice calls
VAPI_PHONE_NUMBER_ID=your_phone_id   # Optional
VAPI_ASSISTANT_ID=your_assistant_id  # Optional
```

**Getting a Gemini API Key:**
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click "Create API Key"
3. Copy the key into `.env`

**Getting a Gmail App Password (for email):**
1. Enable 2-Factor Authentication on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Copy the 16-character password into `.env`

### 3. Run Migrations & Start
```bash
python manage.py migrate
python manage.py runserver
```

Visit **http://localhost:8000** in your browser.

### 4. (Optional) Create Admin User
```bash
python manage.py createsuperuser
```
Access the admin dashboard at **http://localhost:8000/admin/** to view sessions, messages, and appointments.

## Architecture

```
kyron_clinic/
├── manage.py
├── .env                    # API keys (not committed)
├── requirements.txt
├── kyron_medical/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── chat/                   # Main application
│   ├── ai_engine.py        # Gemini AI conversation handler
│   ├── doctors.py          # Hard-coded doctor data & availability
│   ├── models.py           # ChatSession, ChatMessage, Appointment
│   ├── views.py            # API endpoints
│   ├── urls.py
│   ├── admin.py
│   └── templates/chat/
│       └── index.html      # Main chat interface
├── static/
│   ├── css/styles.css      # Liquid glass UI styles
│   └── js/chat.js          # Chat controller
└── db.sqlite3              # SQLite database
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Main chat interface |
| `/api/send-message/` | POST | Send a chat message, get AI response |
| `/api/voice-call/` | POST | Initiate Vapi voice call with context |
| `/api/reset/` | GET | Reset chat session |
| `/api/sms-opt-in/` | POST | Opt in for SMS notifications |
| `/admin/` | GET | Django admin dashboard |

## Doctors & Specialties

| Doctor | Specialty | Body Parts |
|---|---|---|
| Dr. Sarah Chen | Orthopedic Specialist | Knee, hip, shoulder, back, spine, joints |
| Dr. Raj Patel | Cardiologist | Heart, chest, blood pressure, circulation |
| Dr. Elena Martinez | Gastroenterologist | Stomach, digestive, liver, abdomen |
| Dr. Michael Thompson | Neurologist | Head, brain, headache, nerve, dizziness |
| Dr. Aisha Williams | Dermatologist | Skin, rash, acne, hair, nails |

## Deployment (AWS EC2)

1. Launch an EC2 instance (Ubuntu 22.04, t2.micro or larger)
2. Install Python 3.11+, nginx, certbot
3. Clone the repo and configure `.env`
4. Run with gunicorn: `gunicorn kyron_medical.wsgi:application --bind 0.0.0.0:8000`
5. Configure nginx as reverse proxy with SSL via certbot

## Tech Stack

- **Backend:** Django 5.x
- **AI:** Google Gemini 2.0 Flash (via `google-genai`)
- **Voice:** Vapi.ai
- **Email:** Gmail SMTP
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Frontend:** Vanilla JS, CSS with liquid glass effects

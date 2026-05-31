# MediSched AI - Healthcare Scheduling System

## 🏥 Professional Healthcare Management Platform

MediSched AI is a comprehensive, enterprise-grade healthcare scheduling and management system with AI-powered calling, SMS notifications, and advanced analytics.

---

## 📋 Table of Contents

1. [Features](#features)
2. [Technology Stack](#technology-stack)
3. [System Requirements](#system-requirements)
4. [Installation Guide](#installation-guide)
5. [Configuration](#configuration)
6. [Running the Application](#running-the-application)
7. [User Guide](#user-guide)
8. [API Documentation](#api-documentation)
9. [Troubleshooting](#troubleshooting)
10. [Support](#support)

---

## ✨ Features

### Core Features
- ✅ **User Authentication** - Secure JWT-based authentication with auto token refresh
- ✅ **Patient Management** - Complete CRUD operations for patient records
- ✅ **Doctor Management** - Manage doctor profiles, specializations, and availability
- ✅ **Appointment Scheduling** - Smart scheduling with conflict detection
- ✅ **Availability Management** - Flexible slot management for doctors

### Communication Features
- ✅ **AI-Powered Calling** - Automated appointment reminders via Twilio
- ✅ **SMS Notifications** - Send appointment confirmations and reminders
- ✅ **Email Reminders** - Automated email notifications
- ✅ **Call Transcription** - AI-powered call transcription using OpenAI Whisper

### Analytics & Reporting
- ✅ **Interactive Dashboard** - Real-time statistics and metrics
- ✅ **Visual Analytics** - 4 interactive charts powered by Chart.js
  - Appointments Overview (Doughnut Chart)
  - Call Outcomes (Bar Chart)
  - Doctor Utilization (Horizontal Bar Chart)
  - Slot Utilization (Pie Chart)
- ✅ **Data Export** - Export data to CSV for analysis
  - Appointments Export
  - Patients Export
  - Doctors Export
  - Call Logs Export

### Technical Features
- ✅ **Real-time Updates** - WebSocket support via Django Channels
- ✅ **Background Tasks** - Celery for asynchronous task processing
- ✅ **RESTful API** - Comprehensive API with OpenAPI documentation
- ✅ **Professional UI** - Modern, responsive corporate design
- ✅ **Security** - CORS, CSRF protection, secure password hashing

---

## 🛠 Technology Stack

### Backend
- **Framework**: Django 5.0.3
- **API**: Django REST Framework
- **Database**: PostgreSQL 18
- **Cache/Queue**: Redis
- **Task Queue**: Celery
- **ASGI Server**: Daphne (for WebSockets)
- **Authentication**: JWT (Simple JWT)

### Frontend
- **Framework**: React (Development Server)
- **UI**: Pure HTML/CSS/JavaScript
- **Charts**: Chart.js 4.4.0
- **Theme**: Professional Corporate Design

### Integrations
- **Twilio**: AI Calling & SMS
- **OpenAI**: Call Transcription (Whisper)
- **Gmail SMTP**: Email Notifications

---

## 💻 System Requirements

### Required Software
- **Python**: 3.10 or higher
- **Node.js**: 16.x or higher
- **PostgreSQL**: 18.x
- **Redis**: Latest stable version

### Operating System
- Windows 10/11
- macOS 10.15+
- Linux (Ubuntu 20.04+)

### Hardware Requirements
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 2GB free space
- **CPU**: Dual-core processor or better

---

## 📦 Installation Guide

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd medshield-ai
```

### Step 2: Install PostgreSQL

1. Download PostgreSQL 18 from https://www.postgresql.org/download/
2. Install with default settings
3. Remember the password you set for the `postgres` user
4. Create database:

```sql
CREATE DATABASE medisched_db;
```

### Step 3: Install Redis

**Windows:**
- Download from https://github.com/microsoftarchive/redis/releases
- Install and start the service

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

### Step 4: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# Email: admin@medisched.com
# Password: admin123

# Load demo data (optional)
python manage.py seed_demo
```

### Step 5: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Build for production (optional)
npm run build
```

---

## ⚙️ Configuration

### Backend Configuration (.env)

Create `backend/.env` file:

```env
# PostgreSQL Configuration
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/medisched_db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME=15
JWT_REFRESH_TOKEN_LIFETIME=10080

# Twilio Configuration (Optional - for AI Calling & SMS)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# OpenAI Configuration (Optional - for Call Transcription)
OPENAI_API_KEY=your_openai_api_key

# Email Configuration (Optional - for Email Reminders)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

### Important Notes:

1. **PostgreSQL Password**: Replace `YOUR_PASSWORD` with your actual PostgreSQL password
2. **Secret Key**: Generate a secure secret key for production
3. **Twilio**: Sign up at https://www.twilio.com/ for calling/SMS features
4. **OpenAI**: Get API key from https://platform.openai.com/ for transcription
5. **Gmail**: Use App Password, not regular password

---

## 🚀 Running the Application

### Option 1: Using Batch Scripts (Windows)

```bash
# Start all services
START_ALL_SERVICES.bat

# Stop all services
STOP_ALL_SERVICES.bat
```

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
.\venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 - Celery Worker:**
```bash
cd backend
.\venv\Scripts\activate
celery -A config worker -l info --pool=solo
```

**Terminal 3 - Celery Beat (Optional - for scheduled tasks):**
```bash
cd backend
.\venv\Scripts\activate
celery -A config beat -l info
```

**Terminal 4 - Frontend:**
```bash
cd frontend
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/api/schema/swagger-ui/

### Default Login Credentials

```
Email: admin@medisched.com
Password: admin123
```

**⚠️ IMPORTANT**: Change these credentials in production!

---

## 📖 User Guide

### Dashboard
- View real-time statistics
- Monitor appointments, patients, doctors
- Track call logs and SMS messages

### Patient Management
1. Click "Patients" in sidebar
2. Click "Add Patient" button
3. Fill in patient details
4. Save to create new patient
5. Edit or delete existing patients

### Doctor Management
1. Click "Doctors" in sidebar
2. Click "Add Doctor" button
3. Enter doctor information
4. Set specialization and contact details
5. Manage doctor availability

### Appointment Scheduling
1. Click "Appointments" in sidebar
2. Click "Book Appointment" button
3. Select patient and doctor
4. Choose available time slot
5. Add notes if needed
6. Confirm booking

### AI Calling
1. Go to "Call Logs" page
2. Click "Initiate Call" button
3. Select patient
4. Choose call type:
   - General Call
   - Appointment Reminder
   - Appointment Confirmation
   - Slot Offer
   - Follow-up
5. Call will be queued and processed

### SMS Messages
1. Go to "SMS Messages" page
2. Click "Send SMS" button
3. Select patient
4. Choose message type
5. Enter or use template message
6. Send SMS

### Analytics
1. Click "Analytics" in sidebar
2. View interactive charts
3. Export data using export buttons
4. Download CSV files for analysis

---

## 📚 API Documentation

### Authentication Endpoints

**Login**
```http
POST /api/v1/auth/login/
Content-Type: application/json

{
  "email": "admin@medisched.com",
  "password": "admin123"
}

Response:
{
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token",
  "user": {
    "id": 1,
    "email": "admin@medisched.com",
    "role": "ADMIN"
  }
}
```

**Refresh Token**
```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "jwt_refresh_token"
}

Response:
{
  "access": "new_jwt_access_token"
}
```

### Patient Endpoints

**List Patients**
```http
GET /api/v1/patients/
Authorization: Bearer {access_token}
```

**Create Patient**
```http
POST /api/v1/patients/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "full_name": "John Doe",
  "phone_number": "+1234567890",
  "email": "john@example.com",
  "date_of_birth": "1990-01-01",
  "gender": "MALE"
}
```

### Complete API Documentation

Visit http://localhost:8000/api/schema/swagger-ui/ for interactive API documentation.

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Login Error: "Server returned an invalid response"

**Solution:**
- Clear browser cache (Ctrl+Shift+Delete)
- Use incognito mode
- Check if backend is running on port 8000

#### 2. PostgreSQL "too many clients" Error

**Solution:**
```bash
# Restart PostgreSQL service
# Windows:
net stop postgresql-x64-18
net start postgresql-x64-18

# Or use Services (services.msc)
```

**Prevention:**
Edit `C:\Program Files\PostgreSQL\18\data\postgresql.conf`:
```
max_connections = 300  # Increase from 100
```

#### 3. 401 Authentication Errors

**Solution:**
- Auto token refresh is enabled on all pages
- If persists, logout and login again
- Check if JWT tokens are being stored in localStorage

#### 4. Celery Tasks Not Running

**Solution:**
- Ensure Redis is running
- Check Celery worker is started
- Verify CELERY_BROKER_URL in settings

#### 5. Email Not Sending

**Solution:**
- Check EMAIL_HOST_PASSWORD is set in .env
- Use Gmail App Password, not regular password
- Enable "Less secure app access" or use App Password

#### 6. Twilio Calls Not Working

**Solution:**
- Verify Twilio credentials in .env
- For trial accounts, verify phone numbers in Twilio Console
- Check phone numbers are in E.164 format (+1234567890)

---

## 📁 Project Structure

```
medshield-ai/
├── backend/
│   ├── config/              # Django settings and configuration
│   ├── users/               # User authentication
│   ├── patients/            # Patient management
│   ├── doctors/             # Doctor management
│   ├── scheduling/          # Appointments and slots
│   ├── calling/             # AI calling system
│   ├── sms/                 # SMS messaging
│   ├── reminders/           # Email reminders
│   ├── analytics/           # Analytics and reporting
│   ├── transcriptions/      # Call transcription
│   ├── realtime/            # WebSocket support
│   ├── manage.py            # Django management
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── public/              # Static HTML pages
│   │   ├── js/              # JavaScript utilities
│   │   ├── styles/          # CSS stylesheets
│   │   ├── login-corporate.html
│   │   ├── dashboard-corporate.html
│   │   ├── patients-corporate.html
│   │   ├── doctors-corporate.html
│   │   ├── appointments-corporate.html
│   │   ├── slots-corporate.html
│   │   ├── call-logs-corporate.html
│   │   ├── test-sms.html
│   │   ├── reminders-corporate.html
│   │   └── analytics-corporate.html
│   ├── package.json         # Node dependencies
│   └── vite.config.js       # Build configuration
│
├── README.md                # This file
├── SETUP_GUIDE.txt          # Detailed setup instructions
├── COMPLETE_SYSTEM_STATUS.txt  # System status report
├── START_ALL_SERVICES.bat   # Start all services (Windows)
└── STOP_ALL_SERVICES.bat    # Stop all services (Windows)
```

---

## 🔒 Security Best Practices

### For Production Deployment

1. **Change Default Credentials**
   - Update admin password
   - Generate new SECRET_KEY

2. **Environment Variables**
   - Never commit .env files
   - Use environment-specific configurations

3. **Database Security**
   - Use strong PostgreSQL password
   - Restrict database access
   - Enable SSL connections

4. **HTTPS**
   - Use SSL certificates
   - Enable HTTPS only
   - Set secure cookie flags

5. **CORS Configuration**
   - Restrict allowed origins
   - Update CORS_ALLOWED_ORIGINS in settings

6. **Rate Limiting**
   - Implement API rate limiting
   - Use Django throttling

---

## 📊 Performance Optimization

### Database Optimization
- Use connection pooling
- Add database indexes
- Optimize queries with select_related/prefetch_related

### Caching
- Enable Redis caching
- Cache frequently accessed data
- Use Django cache framework

### Frontend Optimization
- Minify JavaScript and CSS
- Enable gzip compression
- Use CDN for static files

---

## 🤝 Support

### Getting Help

1. **Documentation**: Check this README and other .txt files
2. **Logs**: Check `backend/logs/django.log` for errors
3. **API Docs**: Visit http://localhost:8000/api/schema/swagger-ui/
4. **Status File**: Check `COMPLETE_SYSTEM_STATUS.txt`

### Reporting Issues

When reporting issues, include:
- Error message
- Steps to reproduce
- System information
- Log files

---

## 📝 License

Copyright © 2026 MediSched AI. All rights reserved.

---

## 🎉 Acknowledgments

- Django REST Framework
- React
- Chart.js
- Twilio
- OpenAI
- PostgreSQL
- Redis
- Celery

---

## 📞 Contact

For support and inquiries:
- Email: support@medisched.com
- Website: https://medisched.com

---

**Built with ❤️ for Healthcare Professionals**
# medsheild-ai

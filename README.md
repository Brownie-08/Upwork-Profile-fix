# 🚛 LusitoHub - Transport & Freelancing Platform

[![Django](https://img.shields.io/badge/Django-4.x-green.svg)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](.github/workflows/ci.yml)

A comprehensive Django-based platform that combines **transport services** (taxi & delivery) with **freelancing capabilities**, designed specifically for the Eswatini market. The platform enables seamless connections between service providers and clients while managing complex workflows for document verification, payment processing, and real-time communication.

> **Note**: This repository contains enhanced work specifically focused on the **`profiles/` folder** - the core user management and verification system of the LusitoHub platform.

## 🌟 Key Features

### 🚗 Transport Services
- **Taxi & Delivery Services** with real-time booking
- **Google Maps Integration** for route planning and tracking
- **Dynamic Pricing System** with distance-based calculations
- **Bidding System** for competitive pricing
- **Vehicle Management** with document verification
- **Government Permit Workflow** for authorized providers

### 👥 User Management & Verification
- **Multi-tier Profile System** (Regular, Transport Provider)
- **Document Verification System** (ID, Driver's License, Vehicle Documents)
- **Identity Verification** with face photo matching
- **Operator Assignment System** for vehicle management
- **Transport Owner Badge** for verified providers

### 💰 Financial Systems
- **MTN Mobile Money Integration** (MoMo API)
- **Comprehensive Wallet System**
- **Transaction Management** with audit trails
- **Admin Financial Dashboard** with reporting

### 💬 Communication & Notifications
- **Real-time Chat System** with WebSocket support
- **File Sharing & Attachments** in chat
- **Smart Notification System** with multiple channels
- **SMS Integration** (OTP, notifications)
- **Email Notifications** for important events

### 🎯 Freelancing Platform
- **Project Management System**
- **Portfolio Showcase** with samples
- **Rating & Review System**
- **Skills-based Matching**

## 🔐 User Authentication & Security

### Registration Flow
- **Step 1**: User fills out registration form with personal details, email, and optional referral code
- **Step 2**: Verification code is sent directly to user's email (implemented secure email delivery via SMTP instead of console)
- **Step 3**: User enters verification code to activate account
- **Step 4**: Upon verification, user is assigned a unique referral code and can start building their profile

### Identity Verification System
- **Document Upload**: Secure upload of government ID and proof of residence
- **Face Photo Capture**: Advanced dual-option interface for identity verification:
  - Direct webcam capture with face positioning overlay
  - Alternative file upload option for JPG/PNG photos
- **Admin Verification**: Documents are reviewed by admins for approval/rejection
- **Status Tracking**: Users see real-time status of their verification documents in the profile

### Password Management
- **Secure Reset Flow**: Email-based password reset using unique verification codes
- **Password Strength Validation**: Ensures strong passwords with validation rules
- **Account Recovery**: Multiple paths for account recovery including email and phone (where available)

## 👤 Profile System

### Profile CRUD Operations

#### Basic Profile Management
- **Profile Creation**: Auto-generated upon registration with ability to customize
- **Profile Editing**: Comprehensive form with personal and professional details
- **Profile Viewing**: Public and private views with appropriate permission handling
- **Profile Deletion**: Account deactivation with data retention policy

#### Education Management
- **Add**: Add education entries with institution, degree, field, start/end dates
- **Edit**: Modify existing education entries with proper validation
- **View**: Display education history in chronological order
- **Delete**: Remove education entries with confirmation

#### Experience Management
- **Add**: Add work experience with company, title, duration, and description
- **Edit**: Update experience entries with validation for date ranges
- **View**: Chronological display of work history
- **Delete**: Remove experience entries with confirmation

#### Portfolio Management
- **Add**: Create portfolio entries with title, description, completion date
- **Edit**: Update portfolio details and associated samples
- **View**: Showcase portfolio items with rich media support
- **Delete**: Remove portfolio entries with proper cleanup of associated files

### Identity Verification

#### Document Upload System
- **ID Card Upload**: Support for PDF, JPG and PNG formats with size validation
- **Proof of Residence**: Document verification with admin approval workflow
- **Face Photo Capture**: Dual-option capture system:
  - **Webcam Capture**: Interactive interface with positioning overlay and live preview
  - **File Upload**: Alternative for users without webcam access
- **Verification Status**: Clear indication of document verification status

#### Face Photo Capture Features
- **Live Preview**: Real-time webcam feed with positioning guidance
- **Capture Button**: Single-click photo capture functionality
- **Retake Option**: Ability to retake photos until satisfied
- **Face Positioning Overlay**: Visual guide to ensure proper framing
- **Responsive Design**: Works across desktop and mobile devices
- **Fallback File Upload**: Alternative upload method if webcam unavailable
- **Secure Processing**: Base64 encoding and secure transmission

### Referral System

- **Automatic Generation**: Each user receives a unique referral code upon registration
- **Referral Tracking**: Users can view number of people they've referred
- **Referral Sharing**: Easy copying and sharing of referral links
- **Referral Attribution**: New users are properly linked to referring users
- **Referral Dashboard**: Displays referral statistics and user performance

## 🚗 Vehicle Registration & Management

### Vehicle Registration
- **Multi-step Process**: Guided registration flow for vehicle owners
- **Document Requirements**: Upload of required vehicle documents:
  - Registration Certificate (Blue Book)
  - Roadworthiness Certificate
  - Insurance Documentation
  - Driver's License
- **Status Tracking**: Clear indication of verification status for each document
- **Admin Approval**: Review workflow for document verification

### Vehicle Status Display
- **Fixed Status Visibility**: Vehicle status now displays correctly on profile for all users
- **Document Status Indicators**: Clear visual representation of each document's verification status
- **Verification Progress**: Status tracking for the overall vehicle verification process

### Operator Assignment System
- **Operator Management**: Vehicle owners can assign operators (drivers) to their vehicles
- **Document Verification**: Operators must upload valid driver's licenses
- **Status Tracking**: Clear indication of operator verification status
- **Assignment History**: Record of all past and present vehicle operators

### Key Fixes in Vehicle Display
- **Status Visibility**: Fixed conditional display logic to show vehicles regardless of account type
- **Document Status Accuracy**: Improved document status indicators to correctly reflect backend verification status
- **Insurance Document Logic**: Corrected insurance document handling as required documentation
- **Driver's License Display**: Fixed display of driver's license verification status for non-owner operators

## ⚙️ Admin Workflow

### Document Verification Dashboard
- **Queue Management**: Organized workflow for pending document verifications
- **Document Review**: Side-by-side comparison of uploaded documents with user information
- **Approval/Rejection**: Single-click approval or rejection with required reason for rejections
- **Audit Trail**: Complete logging of all verification actions for accountability

### Vehicle Verification Process
1. **Document Submission**: Users upload required vehicle documents
2. **Admin Review**: Admins review documents in specialized verification dashboard
3. **Document Approval/Rejection**: Individual approval/rejection of each document
4. **Verification Status**: Automatic updating of verification status based on document approvals
5. **User Notification**: Real-time notifications to users about approval/rejection

### Identity Verification Workflow
1. **ID Document Upload**: User uploads government ID and proof of residence
2. **Face Photo Submission**: User captures or uploads face photo
3. **Admin Comparison**: Admin compares face photo with ID documents
4. **Verification Decision**: Approval or rejection with feedback
5. **Status Update**: User's verification status is updated automatically

### Email System Configuration
- **SMTP Integration**: Configured for production email delivery via Gmail SMTP
- **Template-based Emails**: Standardized templates for all system communications
- **Delivery Monitoring**: Tracking of email delivery and open rates
- **Bounce Handling**: Management of failed email deliveries

## 📱 Mobile Responsiveness

The platform is fully responsive with:
- **Progressive Web App (PWA)** capabilities
- **Touch-optimized interfaces** for mobile users
- **Offline functionality** for core features
- **Push notifications** support

## 🏗️ System Architecture

### Backend Stack
- **Django 4.x** - Main web framework
- **Django Channels** - WebSocket support for real-time features
- **Django REST Framework** - API endpoints
- **PostgreSQL/SQLite** - Database options
- **Redis** - Caching and channel layer
- **Celery** - Background task processing

### Frontend Technologies
- **HTML5/CSS3** with responsive design
- **Bootstrap 4** - UI components
- **JavaScript/jQuery** - Interactive features
- **Crispy Forms** - Form styling
- **Tailwind CSS** - Modern styling

### Third-Party Integrations
- **Google Maps API** - Location services
- **MTN MoMo API** - Mobile payments
- **Twilio/AWS SNS** - SMS services
- **Jazzmin** - Enhanced admin interface

## 📱 Core Applications

### `profiles` - User Management
```python
# Key Models
- Profile: Extended user profiles with verification status
- Vehicle: Vehicle management with ownership tracking
- Document: File upload and verification system
- DocumentReview: Admin approval workflow
- OperatorAssignment: Driver-vehicle relationships
- TransportOwnerBadge: Authorization system
- GovernmentPermit: Permit management
- LoginOTP: SMS-based authentication
```

### `transport` - Transport Services
```python
# Key Models  
- TransportRequest: Taxi/delivery job requests
- TransportBid: Competitive bidding system
- TransportContract: Job agreements
```

### `wallets` - Financial Management
```python
# Key Models
- Wallet: User financial accounts
- Transaction: Payment records
- MomoPayment: Mobile money integration
```

### `chat` - Real-time Communication
```python
# Key Models
- ChatRoom: Conversation spaces
- Message: Chat messages
- MessageAttachment: File sharing
```

### `notifications` - Notification System
```python
# Key Models
- Notification: System notifications
- NotificationSettings: User preferences
```

### `projects` - Freelancing Platform
```python
# Key Models
- Project: Freelance projects
- Bid: Project proposals
- Contract: Project agreements
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js (for frontend dependencies)
- PostgreSQL (recommended) or SQLite
- Redis (for production)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Brownie-08/Upwork-Profile-fix.git
   cd main_project
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Load sample data (optional)**
   ```bash
   python manage.py loaddata fixtures/sample_data.json
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

### Environment Variables

```env
# Django Core
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
SITE_URL=http://127.0.0.1:8000

# Database
DATABASE_URL=postgres://user:password@localhost:5432/lusitohub

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# Google Maps
Server-Side_API_KEY=your-server-side-key
Client_API_KEY=your-client-side-key

# MTN MoMo
MOMO_SUBSCRIPTION_KEY=your-momo-key
MOMO_API_USER_ID=your-user-id
MOMO_API_KEY=your-api-key
MOMO_ENVIRONMENT=sandbox

# SMS Configuration
SMS_API_KEY=your-sms-key
SMS_SENDER=YourApp
```

## 🧪 Testing

The project includes comprehensive test suites for all major components:

### Run All Tests
```bash
python manage.py test
```

### Run Specific Test Suites
```bash
# Profile system tests
python manage.py test profiles.tests

# Transport system tests  
python manage.py test transport.tests

# Wallet system tests
python manage.py test wallets.tests

# OTP and SMS tests
python manage.py test profiles.tests.test_otp

# Document workflow tests
python manage.py test profiles.tests.test_vehicle_workflow
```

### Test Coverage
- **Profiles App**: 90%+ coverage including OTP, referrals, permits
- **Transport App**: Complete workflow testing
- **Wallets App**: Transaction and MoMo integration tests
- **Integration Tests**: End-to-end workflow validation

## 📊 Admin Dashboard

Access the enhanced admin dashboard at `/admin/` with features:

- **🎨 Custom Jazzmin Theme** matching the main application
- **📈 Financial Overview Dashboard** with transaction analytics
- **🚛 Transport Management** with bulk operations
- **📋 Document Review Interface** for verification workflows
- **👥 User Management** with advanced filtering
- **💰 Payment Processing** with MoMo integration monitoring

## 🔧 Key Workflows

### Document Verification Process
1. User uploads required documents (ID, License, Vehicle Papers)
2. Admin reviews documents in the verification dashboard
3. Automatic notifications sent on approval/rejection
4. Transport Owner Badge granted for verified providers
5. API endpoints provide real-time status updates

### Transport Request Flow
1. Client creates transport request with pickup/dropoff
2. Google Maps calculates route and pricing
3. Verified providers can place bids
4. Client selects preferred bid
5. Contract created with payment escrow
6. Real-time tracking during service
7. Payment released upon completion

### Mobile Payment Integration
1. User initiates payment through wallet
2. MTN MoMo API processes transaction
3. Webhook receives payment confirmation
4. Wallet balance updated automatically
5. Transaction records maintained for audit

## 🌐 API Documentation

### Profile Endpoints
```
GET  /profiles/                    # Profile list
POST /profiles/update/             # Update profile
GET  /profiles/get-permit-status/  # Check permit status  
POST /profiles/upload-permit/      # Upload permit document
POST /profiles/verify-otp/         # OTP verification
```

### Transport Endpoints
```
GET    /transport/requests/        # List transport requests
POST   /transport/requests/        # Create new request
GET    /transport/requests/{id}/   # Request details
POST   /transport/bids/            # Place bid
PUT    /transport/contracts/{id}/  # Update contract
```

### Wallet Endpoints
```
GET  /wallets/balance/            # Get wallet balance
POST /wallets/deposit/            # Deposit funds
POST /wallets/withdraw/           # Withdraw funds  
GET  /wallets/transactions/       # Transaction history
```

## 📱 Mobile Responsiveness

The platform is fully responsive with:
- **Progressive Web App (PWA)** capabilities
- **Touch-optimized interfaces** for mobile users
- **Offline functionality** for core features
- **Push notifications** support

## 🔐 Security Features

### Core Security Measures
- **CSRF Protection** on all forms
- **SQL Injection Prevention** via Django ORM
- **File Upload Validation** with size and type restrictions
- **Rate Limiting** on API endpoints
- **SMS-based Two-Factor Authentication**
- **Secure Payment Processing** with MoMo integration
- **Document Verification** with admin approval workflows

### 🚨 CRITICAL SECURITY WARNINGS

#### Environment Variables & Credentials
```bash
# ⚠️  NEVER commit real credentials to version control!
# ✅  Always use environment variables for sensitive data
# ✅  Rotate credentials regularly
# ✅  Use different credentials for development/production
```

#### Required Security Setup
1. **Generate New Secret Key**: Never use the default Django secret key in production
2. **Email Credentials**: Set up proper SMTP credentials in environment variables
3. **API Keys**: Configure Google Maps, MTN MoMo, and SMS provider keys securely
4. **Database Security**: Use strong passwords and restrict database access
5. **SSL/HTTPS**: Always use HTTPS in production environments

#### Security Checklist
- [ ] All credentials moved to environment variables
- [ ] Production SECRET_KEY generated and secured
- [ ] Database passwords rotated
- [ ] API keys restricted by domain/IP
- [ ] HTTPS configured with valid SSL certificates
- [ ] Security headers configured (HSTS, CSP, etc.)
- [ ] Regular security updates applied

## 🚀 Deployment

### Production Deployment with Docker

1. **Build containers**
   ```bash
   docker-compose -f docker-compose.prod.yml build
   ```

2. **Run services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Setup database**
   ```bash
   docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
   ```

### Manual Deployment

1. **Install production requirements**
   ```bash
   pip install -r requirements.txt
   pip install gunicorn
   ```

2. **Configure static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Run with Gunicorn**
   ```bash
   gunicorn lusitohub.wsgi:application --bind 0.0.0.0:8000
   ```

## 📈 Performance & Scalability

- **Redis Caching** for database query optimization
- **Database Indexing** on frequently queried fields
- **CDN Integration** for static file delivery
- **Async Task Processing** with Celery
- **Connection Pooling** for database efficiency
- **Image Optimization** for profile pictures and documents

## 🤝 Contributing

We welcome contributions to improve LusitoHub! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Development Guidelines
- Follow **PEP 8** style guide for Python code
- Write **comprehensive tests** for new features
- Update **documentation** for any API changes
- Use **meaningful commit messages**

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Admin Dashboard Guide](ADMIN_DASHBOARD_README.md)
- [SMS Integration Guide](SMS_INTEGRATION_GUIDE.md)
- [Permit Workflow Documentation](PERMIT_IMPLEMENTATION_SUMMARY.md)

## 🐛 Known Issues & Roadmap

### Current Limitations
- SMS integration requires provider setup for production
- Real-time chat requires Redis for production scaling
- Google Maps API requires billing account for production

### Upcoming Features
- [ ] **Mobile App** (React Native)
- [ ] **Advanced Analytics Dashboard**
- [ ] **Multi-language Support**
- [ ] **AI-powered Route Optimization**
- [ ] **Blockchain Payment Integration**

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

For support and questions:
- **Email**: support@lusitohub.com
- **GitHub Issues**: [Create an issue](https://github.com/Ncabais/main_project/issues)
- **Documentation**: Check the docs/ directory

## ✅ Completed Profile Module Enhancements

> **Work Focus**: All enhancements listed below were implemented specifically within the **`profiles/` folder** of the Django project, encompassing models, views, forms, templates, and URL configurations for the user management system.

### 🔐 User Authentication & Security
- ✅ **Fixed Email Verification System**: Verification codes now sent directly to user's email using SMTP (not console)
- ✅ **Enhanced Password Reset Flow**: Working password reset with email delivery
- ✅ **Improved Account Verification**: Streamlined registration and verification flow

### 📷 Identity Verification System
- ✅ **Face Photo Capture**: Implemented dual-option system:
  - Webcam capture with positioning overlay and preview
  - Alternative file upload for users without webcam
- ✅ **Document Upload Fix**: Corrected document upload and verification flow
- ✅ **Verification Status Display**: Improved visibility of verification status on profile

### 📚 CRUD Features (Education, Experience, Portfolio)
- ✅ **Fixed Education Management**: Corrected all CRUD operations with proper redirects and feedback
- ✅ **Fixed Experience Management**: Repaired broken CRUD functionality with proper form handling
- ✅ **Fixed Portfolio Management**: Restored full functionality for portfolio items

### 🚗 Vehicle Registration System
- ✅ **Fixed Vehicle Display**: Corrected conditional logic to show vehicles properly on profile
- ✅ **Improved Document Status**: Fixed document verification status display
- ✅ **Corrected Insurance Document Logic**: Insurance now properly treated as required
- ✅ **Fixed Driver's License Display**: Improved verification status logic

### 👨‍✈️ Operator Assignment & Documents
- ✅ **Fixed Operator Display**: Corrected visibility of operator assignments
- ✅ **Improved Document Status**: Fixed operator document verification display
- ✅ **Enhanced Operator Management**: Streamlined operator assignment workflow

### 🤝 Referral System
- ✅ **Fixed Referral Display**: Ensured referral code is visible on profile
- ✅ **Improved Sharing Options**: Enhanced referral sharing capabilities
- ✅ **Fixed Referral Tracking**: Corrected referral count and status display

### 🖼️ Frontend Fixes
- ✅ **Fixed Logo Display**: Corrected image path for platform logo
- ✅ **Improved Template Inheritance**: Fixed base template extension issues
- ✅ **Enhanced Static File Management**: Proper handling of static assets

## 🚑‍💼 Authors

- **Brownie-08** - *Profiles Folder Enhancement Developer* - [GitHub Profile](https://github.com/Brownie-08)
  - Specialized work on the `profiles/` Django app including user authentication, identity verification, CRUD operations, and admin workflow enhancements

## 🙏 Acknowledgments

- Django community for the excellent framework
- Bootstrap team for responsive UI components
- Google Maps API for location services
- MTN for Mobile Money API integration
- Jazzmin for the beautiful admin interface

---

**LusitoHub** - Connecting Eswatini through technology 🇸🇿

*Built with ❤️ using Django and modern web technologies*

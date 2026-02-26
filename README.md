# 🌟 حساباتي - Hisabati

<div align="center">

![Django](https://img.shields.io/badge/Django-4.2+-092E20?style=for-the-badge&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.14+-red?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-20.10+-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**منصة لبيع وشراء حسابات التواصل الاجتماعي في الوطن العربي**

[العربية](#-نظرة-عامة) | [English](#-overview-english)

</div>

---

## 📋 نظرة عامة

**حساباتي** هي منصة إلكترونية متخصصة تتيح للمستخدمين في الوطن العربي شراء وبيع حسابات مواقع التواصل الاجتماعي بشكل آمن وموثوق. توفر المنصة تجربة مستخدم سلسة مع دعم لعدة عملات عربية وتحديد موقع تلقائي للمستخدم.

### ✨ المميزات الرئيسية

- 🔐 **نظام مصادقة متقدم**
  - تسجيل دخول بالبريد الإلكتروني وكلمة المرور
  - تسجيل دخول عبر Google OAuth 2.0
  - التحقق بخطوتين (OTP) عبر البريد الإلكتروني
  - JWT Token Authentication

- 🌍 **دعم متعدد للدول والعملات**
  - كشف تلقائي لموقع المستخدم عبر IP
  - دعم 17+ عملة عربية
  - تحويل الأسعار تلقائياً للعملة المحلية
  - عرض الإعلانات حسب بلد المستخدم

- 📢 **إدارة الإعلانات**
  - إنشاء إعلانات بيع الحسابات
  - تعديل وحذف الإعلانات
  - تصنيف الإعلانات حسب المنصة
  - حالات الإعلانات (نشط، مباع، غير نشط)

- 💼 **لوحة تحكم البائعين**
  - عرض جميع إعلانات البائع
  - إدارة كاملة للإعلانات (CRUD)
  - إحصائيات وتقارير

- ⚡ **الأداء والكفاءة**
  - تخزين مؤقت (Caching) باستخدام Redis
  - استعلامات محسنة مع select_related
  - Pagination للقوائم الطويلة

---

## 🏗️ التقنيات المستخدمة

### Backend
- **Django 4.2+** - إطار عمل الويب
- **Django REST Framework** - بناء RESTful APIs
- **PostgreSQL** - قاعدة البيانات الرئيسية
- **Redis** - التخزين المؤقت والجلسات
- **Simple JWT** - مصادقة JWT

### DevOps & Deployment
- **Docker & Docker Compose** - الحاويات والنشر
- **Podman Compose** - بديل Docker
- **Gunicorn** - WSGI HTTP Server

### External Services
- **Google OAuth 2.0** - تسجيل الدخول بجوجل
- **IP-API / ipapi.co** - كشف الموقع الجغرافي
- **SMTP** - إرسال رسائل OTP

---

## 📦 التثبيت والإعداد

### المتطلبات الأساسية

```bash
- Python 3.10+
- PostgreSQL 15+
- Redis 7.0+
- Docker & Docker Compose (اختياري)
```

### 1. استنساخ المشروع

```bash
git clone https://github.com/yourusername/Bay3_platform.git
cd Bay3_platform
```

### 2. إعداد البيئة الافتراضية

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate  # Windows
```

### 3. تثبيت المكتبات

```bash
pip install -r requirements.txt
```

### 4. إعداد متغيرات البيئة

أنشئ ملف `.env` في المجلد الرئيسي:

```env
# Database
DB_NAME=trusthandle_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email (for OTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@hisabati.com

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 5. تطبيق الهجرات (Migrations)

```bash
python manage.py migrate
```

### 6. إنشاء بيانات تجريبية (اختياري)

```bash
python manage.py seed_data
```

### 7. إنشاء حساب مدير

```bash
python manage.py createsuperuser
```

### 8. تشغيل السيرفر

```bash
python manage.py runserver
```

---

## 🐳 التشغيل باستخدام Docker

```bash
# بناء وتشغيل الحاويات
docker-compose up -d

# أو باستخدام Podman
podman-compose up -d

# تطبيق الهجرات
docker-compose exec web python manage.py migrate

# إنشاء بيانات تجريبية
docker-compose exec web python manage.py seed_data

# إيقاف الحاويات
docker-compose down
```

## 🛠️ الأوامر المفيدة

```bash
# تحديث أسعار العملات
python manage.py update_rates

# إنشاء بيانات تجريبية
python manage.py seed_data

# جمع الملفات الثابتة
python manage.py collectstatic

# فحص المشروع
python manage.py check

# إنشاء ملف الهجرة
python manage.py makemigrations

# تطبيق الهجرات
python manage.py migrate
```

---

## 🤝 المساهمة

نرحب بمساهماتكم! يرجى اتباع الخطوات التالية:

1. Fork المشروع
2. إنشاء فرع جديد (`git checkout -b feature/AmazingFeature`)
3. Commit التغييرات (`git commit -m 'Add some AmazingFeature'`)
4. Push إلى الفرع (`git push origin feature/AmazingFeature`)
5. فتح Pull Request

---

## 📄 الترخيص

هذا المشروع مرخص تحت [MIT License](LICENSE).

--- 

<div align="center">

**صنع بـ ❤️ للعالم العربي**

[![GitHub stars](https://img.shields.io/github/stars/yourusername/Bay3_platform?style=social)](https://github.com/yourusername/Bay3_platform)
[![GitHub forks](https://img.shields.io/github/forks/yourusername/Bay3_platform?style=social)](https://github.com/yourusername/Bay3_platform/fork)

</div>

---

## 📖 Overview (English)

**Hisabati** is a specialized e-commerce platform that enables users across the Arab world to buy and sell social media accounts securely and reliably. The platform provides a seamless user experience with support for multiple Arab currencies and automatic user location detection.

### Key Features

- 🔐 Advanced authentication system (Email/Password, Google OAuth, 2FA OTP)
- 🌍 Multi-country and currency support with automatic IP-based detection
- 📢 Full announcement management (CRUD operations)
- 💼 Seller dashboard with statistics
- ⚡ High performance with Redis caching and optimized queries

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/Bay3_platform.git

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the server
python manage.py runserver
```

For detailed documentation, see the sections above (in Arabic) or check [SELLER_ANNOUNCEMENTS_API.md](SELLER_ANNOUNCEMENTS_API.md) for API documentation.

---

**Made with ❤️ for the Arab World**

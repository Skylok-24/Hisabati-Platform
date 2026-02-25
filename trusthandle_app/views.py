from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer , LoginSerializer
from trusthandle_app.serializers import GoogleLoginSerializer
from django.contrib.auth import get_user_model
import random
import json
import hashlib
from django.conf import settings
from django.core.mail import send_mail
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests
from trusthandle_app.models import Announcement, Country
from trusthandle_app.serializers import AnnouncementSerializer

User = get_user_model()


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip

@api_view(["GET"])
def index(request) :
    ip = get_client_ip(request)

    # أثناء التطوير على localhost
    if ip == "127.0.0.1":
        ip = "197.205.0.1"  # IP جزائري للتجربة

    try:
        res = requests.get(f"https://ipapi.co/{ip}/country/")
        country_iso = res.text.strip()
    except:
        return Response({"error": "Cannot detect country"}, status=400)

    iso_to_currency = {
        # شمال إفريقيا
        "DZ": "DZD",  # Algeria
        "MA": "MAD",  # Morocco
        "TN": "TND",  # Tunisia
        "LY": "LYD",  # Libya
        "EG": "EGP",  # Egypt
        "SD": "SDG",  # Sudan
        "MR": "MRU",  # Mauritania

        # الخليج
        "SA": "SAR",  # Saudi Arabia
        "AE": "AED",  # UAE
        "QA": "QAR",  # Qatar
        "KW": "KWD",  # Kuwait
        "BH": "BHD",  # Bahrain
        "OM": "OMR",  # Oman

        # بلاد الشام
        "JO": "JOD",  # Jordan
        "LB": "LBP",  # Lebanon
        "SY": "SYP",  # Syria
        "PS": "ILS",  # Palestine (تتعامل غالباً بالشيكل)

        # العراق واليمن
        "IQ": "IQD",  # Iraq
        "YE": "YER",  # Yemen

        # جزر القمر وجيبوتي
        "KM": "KMF",  # Comoros
        "DJ": "DJF",  # Djibouti

        # الصومال
        "SO": "SOS",  # Somalia
    }

    currency_code = iso_to_currency.get(country_iso)

    if not currency_code:
        return Response({"error": "Country not supported"}, status=404)

    try:
        country = Country.objects.get(currency_code=currency_code)
    except Country.DoesNotExist:
        return Response({"error": f"Country not found in database {country_iso}"}, status=404)

    announcements = Announcement.objects.filter(
        seller__country=country,
        status="active"
    ).order_by("-created_at")

    serializer = AnnouncementSerializer(announcements, many=True)

    return Response({
        "country": country.name,
        "currency": country.currency_code,
        "count": announcements.count(),
        "data": serializer.data
    })


@api_view(['POST'])
def login_view(request) :
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid() :
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "refresh_token": str(refresh),
            "access_token": str(refresh.access_token)
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors,status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
def register(request):
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():

        data = serializer.validated_data
        email = data['email']
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "Email already registered"},
                status=400
            )

        otp_code = str(random.randint(100000, 999999))
        hashed_otp = hashlib.sha256(otp_code.encode()).hexdigest()

        redis_client = settings.REDIS_CLIENT

        # نحفظ بيانات المستخدم مؤقتاً
        redis_client.setex(
            f"pending_user_{email}",
            300,
            json.dumps({
                "full_name": data['full_name'],
                "email": email,
                "password": data['password']
            })
        )

        # نحفظ OTP
        redis_client.setex(f"otp_{email}", 300, hashed_otp)

        send_mail(
            subject="رمز التحقق",
            message=f"رمز التحقق هو: {otp_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        return Response({"message": "OTP sent"}, status=201)

    return Response(serializer.errors, status=400)


@api_view(['POST'])
def verify_otp(request):
    email = request.data.get("email")
    code = request.data.get("code")

    redis_client = settings.REDIS_CLIENT

    stored_otp = redis_client.get(f"otp_{email}")
    pending_user = redis_client.get(f"pending_user_{email}")

    if not stored_otp or not pending_user:
        return Response({"error": "Invalid or expired OTP"}, status=400)

    # حماية من brute force
    attempts_key = f"otp_attempts_{email}"
    attempts = redis_client.incr(attempts_key)
    redis_client.expire(attempts_key, 300)

    if attempts > 5:
        return Response({"error": "Too many attempts. Try again later."}, status=429)

    hashed_input = hashlib.sha256(code.encode()).hexdigest()

    import hmac
    if not hmac.compare_digest(stored_otp, hashed_input):
        return Response({"error": "Invalid or expired OTP"}, status=400)

    user_data = json.loads(pending_user)

    if User.objects.filter(email=email).exists():
        return Response({"error": "User already exists"}, status=400)

    user = User.objects.create_user(
        full_name=user_data['full_name'],
        email=user_data['email'],
        password=user_data['password']
    )

    redis_client.delete(f"otp_{email}")
    redis_client.delete(f"pending_user_{email}")
    redis_client.delete(attempts_key)

    refresh = RefreshToken.for_user(user)

    return Response({
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "refresh_token": str(refresh),
        "access_token": str(refresh.access_token)
    })


@api_view(['POST'])
def google_login(request):
    serializer = GoogleLoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    token = serializer.validated_data["id_token"]

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID  # ضع Client ID هنا
        )
    except ValueError:
        return Response({"detail": "Invalid Google token"}, status=400)

    email = idinfo.get("email")
    name = idinfo.get("name")
    email_verified = idinfo.get("email_verified")

    if not email or not email_verified:
        return Response({"detail": "Email not verified"}, status=400)

    user, created = User.objects.get_or_create(
        email=email,
        defaults={"full_name": name}
    )

    if created:
        user.set_unusable_password()
        user.save()

    if not user.is_active:
        return Response({"detail": "Account disabled"}, status=403)

    if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
        return Response({"detail": "Wrong issuer"}, status=400)

    refresh = RefreshToken.for_user(user)

    return Response({
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "refresh_token": str(refresh),
        "access_token": str(refresh.access_token)
    })









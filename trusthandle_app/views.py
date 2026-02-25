from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer , LoginSerializer
import requests
from trusthandle_app.serializers import GoogleLoginSerializer
from django.contrib.auth import get_user_model
import random
import json
import hashlib
from django.conf import settings
from django.core.mail import send_mail

User = get_user_model()


def index(request) :
    return Response({
        "message" : "index page"
    },status=status.HTTP_200_OK)

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
            from_email="your_email@gmail.com",
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
def google_login(request) :
    serializer = GoogleLoginSerializer(data=request.data)

    if not serializer.is_valid() :
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

    access_token = serializer.validated_data['access_token']

    google_url = "https://www.googleapis.com/oauth2/v3/userinfo"

    response = requests.get(
        google_url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )

    if response.status_code != 200:
        return Response(
            {"detail": "Invalid Google token"},
            status=status.HTTP_400_BAD_REQUEST
        )

    data = response.json()

    email = data.get("email")
    if not email:
        return Response(
            {"detail": "Google account has no email"},
            status=status.HTTP_400_BAD_REQUEST
        )
    name = data.get("name")
    email_verified = data.get("email_verified")

    if not email_verified:
        return Response(
            {"detail": "Email not verified by Google"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user, created = User.objects.get_or_create(
        email=email,
        defaults={"full_name": name}
    )

    if created:
        user.set_unusable_password()
        user.save()

    if not user.is_active:
        return Response(
            {"detail": "Account disabled"},
            status=status.HTTP_403_FORBIDDEN
        )

    refresh = RefreshToken.for_user(user)

    return Response({
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "refresh_token": str(refresh),
        "access_token": str(refresh.access_token)
    }, status=status.HTTP_200_OK)


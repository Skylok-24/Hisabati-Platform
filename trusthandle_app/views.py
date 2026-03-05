from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    RegisterSerializer, LoginSerializer, AnnouncementUpdateSerializer, 
    AnnouncementCreateSerializer, SellerSerializer, ChangePasswordSerializer,
    ResetPasswordRequestSerializer, ResetPasswordConfirmSerializer, ResendOTPSerializer
)
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
from trusthandle_app.models import Announcement, Country, Seller
from trusthandle_app.serializers import AnnouncementSerializer
from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated , AllowAny, BasePermission
from rest_framework.decorators import api_view, permission_classes
from .pagination import TenPerPagePagination
from rest_framework.exceptions import NotFound, ValidationError


ISO_TO_CURRENCY = {
    # شمال إفريقيا
    "DZ": "DZD",
    "MA": "MAD",
    "TN": "TND",
    "LY": "LYD",
    "EG": "EGP",
    "SD": "SDG",
    "MR": "MRU",

    # الخليج
    "SA": "SAR",
    "AE": "AED",
    "QA": "QAR",
    "KW": "KWD",
    "BH": "BHD",
    "OM": "OMR",

    # بلاد الشام
    "JO": "JOD",
    "LB": "LBP",
    "SY": "SYP",
    "PS": "ILS",

    # العراق واليمن
    "IQ": "IQD",
    "YE": "YER",

    # جزر القمر وجيبوتي
    "KM": "KMF",
    "DJ": "DJF",

    # الصومال
    "SO": "SOS",
}



User = get_user_model()


# Custom Permission to check if user is the seller who owns the announcement
class IsSellerOwner(BasePermission):
    """
    Custom permission to only allow sellers to edit or delete their own announcements.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if user is authenticated and is a seller
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has a seller profile
        try:
            seller = Seller.objects.get(user=request.user)
        except Seller.DoesNotExist:
            return False
        
        # Check if the announcement belongs to this seller
        return obj.seller == seller


class CountryAnnouncementsView(ListAPIView):
    serializer_class = AnnouncementSerializer
    pagination_class = TenPerPagePagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        # إرجاع جميع الإعلانات المفعلة فقط مع ترتيبها من الأحدث للأقدم
        return (
            Announcement.objects
            .filter(status="active")
            .select_related(
                "seller__user",
                "seller__country",
                "category"
            )
            .order_by("-created_at")
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_request(request):
    serializer = ResetPasswordRequestSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # We return success even if user doesn't exist for security reasons (email enumeration)
            # but we only send email if user exists.
            return Response({"message": "If an account exists with this email, an OTP has been sent."}, status=status.HTTP_200_OK)

        otp_code = str(random.randint(100000, 999999))
        hashed_otp = hashlib.sha256(otp_code.encode()).hexdigest()
        redis_client = settings.REDIS_CLIENT

        # Store OTP in redis for 10 minutes
        redis_client.setex(f"reset_otp_{email}", 600, hashed_otp)

        send_mail(
            subject="Password Reset OTP",
            message=f"Your OTP for password reset is: {otp_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
        return Response({"message": "If an account exists with this email, an OTP has been sent."}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_confirm(request):
    serializer = ResetPasswordConfirmSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        redis_client = settings.REDIS_CLIENT
        stored_otp = redis_client.get(f"reset_otp_{email}")

        if not stored_otp:
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        hashed_input = hashlib.sha256(otp.encode()).hexdigest()
        import hmac
        if not hmac.compare_digest(stored_otp, hashed_input):
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            redis_client.delete(f"reset_otp_{email}")
            return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_otp(request):
    serializer = ResendOTPSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        reason = serializer.validated_data['reason']
        redis_client = settings.REDIS_CLIENT

        if reason == 'registration':
            pending_user = redis_client.get(f"pending_user_{email}")
            if not pending_user:
                return Response({"error": "No pending registration found for this email."}, status=status.HTTP_400_BAD_REQUEST)

            otp_code = str(random.randint(100000, 999999))
            hashed_otp = hashlib.sha256(otp_code.encode()).hexdigest()

            # Refresh registration data expiration as well
            redis_client.expire(f"pending_user_{email}", 300)
            redis_client.setex(f"otp_{email}", 300, hashed_otp)

            send_mail(
                subject="رمز التحقق (إعادة إرسال)",
                message=f"رمز التحقق الجديد هو: {otp_code}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
            return Response({"message": "OTP resent successfully (Registration)."}, status=status.HTTP_200_OK)

        elif reason == 'reset_password':
            try:
                User.objects.get(email=email)
            except User.DoesNotExist:
                # Security: Don't reveal if user exists, but here if they are resending reset OTP, they likely already requested it
                return Response({"message": "If an account exists with this email, a new OTP has been sent."}, status=status.HTTP_200_OK)

            otp_code = str(random.randint(100000, 999999))
            hashed_otp = hashlib.sha256(otp_code.encode()).hexdigest()

            # Reset OTP for 10 minutes
            redis_client.setex(f"reset_otp_{email}", 600, hashed_otp)

            send_mail(
                subject="Password Reset OTP (Resend)",
                message=f"Your new OTP for password reset is: {otp_code}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
            return Response({"message": "OTP resent successfully (Password Reset)."}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

    if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
        return Response({"detail": "Wrong issuer"}, status=400)

    user, created = User.objects.get_or_create(
        email=email,
        defaults={"full_name": name}
    )

    if created:
        user.set_unusable_password()
        user.save()

    if not user.is_active:
        return Response({"detail": "Account disabled"}, status=403)

    refresh = RefreshToken.for_user(user)

    return Response({
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "refresh_token": str(refresh),
        "access_token": str(refresh.access_token)
    })


class SellerAnnouncementsListView(ListCreateAPIView):
    """
    GET /api/seller/announcements/ : Returns seller profile + paginated announcements.
    POST /api/seller/announcements/ : Creates a new announcement.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = TenPerPagePagination

    def get_serializer_class(self):
        return AnnouncementSerializer

    def get_queryset(self):
        user = self.request.user
        try:
            seller = Seller.objects.get(user=user)
            return Announcement.objects.filter(
                seller=seller
            ).select_related(
                "seller__user",
                "seller__country",
                "category"
            ).order_by("-created_at")
        except Seller.DoesNotExist:
            return Announcement.objects.none()

    def list(self, request, *args, **kwargs):
        user = self.request.user
        try:
            # نجلب بيانات البائع
            seller = Seller.objects.get(user=user)
        except Seller.DoesNotExist:
            raise NotFound({"detail": "Seller profile not found"})

        # نجلب الإعلانات الخاصة به
        queryset = self.filter_queryset(self.get_queryset())

        # نطبق الـ Pagination
        page = self.paginate_queryset(queryset)

        # تجهيز بيانات البائع باستخدام السيريالايزر الخاص به
        seller_data = SellerSerializer(seller).data

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)

            # ندمج الـ Profile مع الـ Paginated Announcements في رد واحد
            return Response({
                "seller_profile": seller_data,
                "announcements_data": paginated_response.data
            })

        # في حال تم إيقاف الـ Pagination لأي سبب
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "seller_profile": seller_data,
            "announcements_data": serializer.data
        })

    def perform_create(self, serializer):
        user = self.request.user
        try:
            seller = Seller.objects.get(user=user)
        except Seller.DoesNotExist:
            raise ValidationError({"detail": "Seller profile not found"})

        serializer.save(seller=seller)

    # def create(self, request, *args, **kwargs):
    #     response = super().create(request, *args, **kwargs)
    #     response.data = {
    #         "message": "Announcement created successfully",
    #         "data": response.data,
    #     }
    #     return response

class AnnouncementDetailView(RetrieveAPIView):
    """
    Retrieve announcement details.
    - GET /api/announcements/{id}/ - Retrieve announcement details
    """
    queryset = Announcement.objects.all()
    lookup_field = 'id'
    serializer_class = AnnouncementSerializer
    permission_classes = [AllowAny]


class SellerAnnouncementManageView(RetrieveUpdateDestroyAPIView):
    """
    Manage seller's own announcements (restricted to seller who owns them).
    - GET /api/seller/announcements/{id}/ - Retrieve own announcement
    - PATCH /api/seller/announcements/{id}/ - Update own announcement
    - DELETE /api/seller/announcements/{id}/ - Delete own announcement
    
    Only the authenticated seller can access their own announcements.
    """
    permission_classes = [IsAuthenticated, IsSellerOwner]
    lookup_field = 'id'

    def get_serializer_class(self):
        """Use different serializers for different methods"""
        if self.request.method in ['PATCH', 'PUT']:
            return AnnouncementUpdateSerializer
        return AnnouncementSerializer

    def get_queryset(self):
        user = self.request.user
        try:
            seller = Seller.objects.get(user=user)
            return Announcement.objects.filter(seller=seller)
        except Seller.DoesNotExist:
            return Announcement.objects.none()

    def perform_update(self, serializer):
        """Save updated announcement"""
        serializer.save()

    def perform_destroy(self, instance):
        """Delete announcement"""
        instance.delete()

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data = {
            "message": "Announcement updated successfully",
            "data": response.data,
        }
        return response

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(
            {"message": "Announcement deleted successfully"},
            status=status.HTTP_200_OK,
        )


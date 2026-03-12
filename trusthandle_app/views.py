from rest_framework.response import Response
from rest_framework import status
import hmac
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    RegisterSerializer, LoginSerializer, AnnouncementUpdateSerializer, 
    AnnouncementCreateSerializer, SellerSerializer, ChangePasswordSerializer,
    ResetPasswordRequestSerializer, ResetPasswordConfirmSerializer, ResendOTPSerializer,
    CountryRateSerializer
)
from trusthandle_app.serializers import GoogleLoginSerializer
from django.contrib.auth import get_user_model
import random
import secrets
import json
import hashlib
from django.conf import settings
from django.core.mail import send_mail
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from trusthandle_app.models import Announcement, Country, Seller , Category
from trusthandle_app.serializers import AnnouncementSerializer , CategorySerializer , CountrySerializer , CountryHomeSerializer , SellerEditProfileSerializer
from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated , AllowAny, BasePermission
from rest_framework.decorators import api_view, permission_classes
from .pagination import TenPerPagePagination
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView
from rest_framework.filters import SearchFilter
from decimal import Decimal, InvalidOperation
from django.shortcuts import get_object_or_404
from django.db.models import Max
from rest_framework.generics import UpdateAPIView
from .email_service import send_otp_email


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


class LogoutView(APIView):
    # نضع الصلاحية لأنه لا يمكن لشخص غير مسجل الدخول أن يعمل تسجيل خروج
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # نستقبل الـ refresh token من الـ Body الخاص بالطلب
            refresh_token = request.data.get("refresh")

            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # نقوم بإنشاء كائن من التوكن ثم نضعه في القائمة السوداء
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"message": "You have successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT
            )
        except Exception as e:
            # إذا كان التوكن غير صحيح أو انتهت صلاحيته بالفعل
            return Response(
                {"error": "The token is invalid or has already been logged out."},
                status=status.HTTP_400_BAD_REQUEST
            )


class CountryAnnouncementsView(ListAPIView):
    serializer_class = AnnouncementSerializer
    pagination_class = TenPerPagePagination
    permission_classes = [AllowAny]

    def get_queryset(self):
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Calculate max values from the full queryset (before pagination)
        aggregates = queryset.aggregate(
            max_followers=Max("followers"),
            max_price=Max("price_usd")
        )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(queryset, many=True)
            response = Response(serializer.data)

        countries = Country.objects.all()
        categories = Category.objects.all()

        countries_data = CountryHomeSerializer(countries, many=True).data
        categories_data = CategorySerializer(categories, many=True).data

        if isinstance(response.data, dict):
            response.data['countries'] = countries_data
            response.data['categories'] = categories_data
            response.data['max_followers'] = aggregates['max_followers'] or 0
            response.data['max_price'] = aggregates['max_price'] or 0

        return response


class AnnouncementSearchView(ListAPIView):
    serializer_class = AnnouncementSerializer
    pagination_class = TenPerPagePagination
    permission_classes = [AllowAny]

    # تفعيل فلتر البحث الخاص بـ DRF
    filter_backends = [SearchFilter]
    # تحديد الحقول التي سيتم البحث فيها (يمكنك إضافة الوصف أيضاً)
    search_fields = ['title', 'description']

    def get_queryset(self):
        # هنا نُرجع فقط الـ QuerySet الأساسي، والـ SearchFilter سيتكفل بالباقي أوتوماتيكياً
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


class AnnouncementFilterView(ListAPIView):
    """
    API for filtering announcements based on multiple criteria:
    - followers (range: min_followers, max_followers)
    - price (range: min_price, max_price) - filtered on price_usd
    - category (category_id)
    - country (country_id)
    """
    serializer_class = AnnouncementSerializer
    pagination_class = TenPerPagePagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = (
            Announcement.objects
            .filter(status="active")
            .select_related(
                "seller__user",
                "seller__country",
                "category"
            )
            .order_by("-created_at")
        )

        # Filter by Followers
        min_followers = self.request.query_params.get('min_followers')
        max_followers = self.request.query_params.get('max_followers')
        if min_followers:
            queryset = queryset.filter(followers__gte=min_followers)
        if max_followers:
            queryset = queryset.filter(followers__lte=max_followers)

        # Filter by Price (using price_usd)
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price_usd__gte=min_price)
        if max_price:
            queryset = queryset.filter(price_usd__lte=max_price)

        # Filter by Category
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Filter by Country (seller's country)
        country_id = self.request.query_params.get('country_id')
        if country_id:
            queryset = queryset.filter(seller__country_id=country_id)

        return queryset


CURRENCY_SYMBOLS = {
    "DZD": "د.ج",
    "MAD": "د.م",
    "TND": "د.ت",
    "LYD": "د.ل",
    "EGP": "ج.م",
    "SDG": "ج.س",
    "MRU": "أ.ق",
    "SAR": "ر.س",
    "AED": "د.إ",
    "QAR": "ر.ق",
    "KWD": "د.ك",
    "BHD": "د.ب",
    "OMR": "ر.ع",
    "JOD": "د.أ",
    "LBP": "ل.ل",
    "SYP": "ل.س",
    "ILS": "ش.ج",
    "IQD": "د.ع",
    "YER": "ر.ي",
    "KMF": "ف.ق",
    "DJF": "ف.ج",
    "SOS": "ش.ص",
}


class CountryRateListView(APIView):
    """
    API that returns the daily exchange rates in a formatted structure for the dashboard.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        countries = Country.objects.all().order_by('name')
        rates_data = []

        for country in countries:
            symbol = CURRENCY_SYMBOLS.get(country.currency_code, country.currency_code)

            try:
                # نستخدم Decimal بدلاً من float لضمان دقة الحسابات المالية
                rate = Decimal(str(country.rate_to_usd))

                if rate > 0:
                    local_value = Decimal('1.00') / rate
                    # تنسيق الرقم: إضافة فواصل للآلاف وتقريبه لرقمين عشريين (مثال: 1,350.50)
                    formatted_value = f"{local_value:,.2f}"
                else:
                    formatted_value = "0.00"

            except (ZeroDivisionError, TypeError, InvalidOperation, ValueError):
                formatted_value = "0.00"

            rates_data.append({
                "usd_amount": "1 USD",
                "local_amount": f"{formatted_value} {symbol}",
                "label": "سعر اليوم",
                # كتابة الزوج بالطريقة المالية المتعارف عليها
                "pair": f"USD / {country.currency_code}"
            })

        response_data = {
            "title": "أسعار الصرف اليوم",
            "description": "يتم عرض الأسعار أدناه بناءً على سعر الدولار الأمريكي (USD) مقابل عملات الدول المدعومة في المنصة.",
            "rates": rates_data
        }

        return Response(response_data, status=status.HTTP_200_OK)


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
            return Response({"message": "If an account exists with this email, a reset link has been sent."}, status=status.HTTP_200_OK)

        token = secrets.token_urlsafe(32)
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        redis_client = settings.REDIS_CLIENT

        # Store token in redis for 1 hour
        redis_client.setex(f"reset_token_{email}", 3600, hashed_token)

        # frontend_url should be defined in settings, but for now we'll use a placeholder or check if it exists
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_link = f"{frontend_url}/reset-password-confirm?token={token}&email={email}"

        send_mail(
            subject="Password Reset Link",
            message=f"Click the link below to reset your password:\n{reset_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
        return Response({"message": "If an account exists with this email, a reset link has been sent."}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_confirm(request):

    email = request.query_params.get("email")
    token = request.query_params.get("token")

    if not email or not token:
        return Response(
            {"error": "Invalid reset link"},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = ResetPasswordConfirmSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    new_password = serializer.validated_data["new_password"]

    redis_client = settings.REDIS_CLIENT
    stored_token_hash = redis_client.get(f"reset_token_{email}")

    if not stored_token_hash:
        return Response(
            {"error": "Invalid or expired reset link"},
            status=status.HTTP_400_BAD_REQUEST
        )

    hashed_input = hashlib.sha256(token.encode()).hexdigest()

    if not hmac.compare_digest(stored_token_hash, hashed_input):
        return Response(
            {"error": "Invalid or expired reset link"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(email=email)

        user.set_password(new_password)
        user.save()

        redis_client.delete(f"reset_token_{email}")

        return Response(
            {"message": "Password reset successfully"},
            status=status.HTTP_200_OK
        )

    except User.DoesNotExist:
        return Response(
            {"error": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )


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

            send_otp_email(email, otp_code)
            return Response({"message": "OTP resent successfully (Registration)."}, status=status.HTTP_200_OK)

        elif reason == 'reset_password':
            try:
                User.objects.get(email=email)
            except User.DoesNotExist:
                # Security: Don't reveal if user exists, but here if they are resending reset link, they likely already requested it
                return Response({"message": "If an account exists with this email, a new reset link has been sent."}, status=status.HTTP_200_OK)

            token = secrets.token_urlsafe(32)
            hashed_token = hashlib.sha256(token.encode()).hexdigest()

            # Reset token for 1 hour
            redis_client.setex(f"reset_token_{email}", 3600, hashed_token)

            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_link = f"{frontend_url}/reset-password-confirm?token={token}&email={email}"

            send_mail(
                subject="Password Reset Link (Resend)",
                message=f"Click the link below to reset your password:\n{reset_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
            return Response({"message": "Reset link resent successfully."}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CountryListView(ListAPIView):
    queryset = Country.objects.all().order_by('name') # ترتيب أبجدي لتسهيل البحث على المستخدم
    serializer_class = CountryHomeSerializer
    permission_classes = [AllowAny] # مسموح لأي شخص (لأن المستخدم ما زال زائر)
    pagination_class = None

@api_view(['POST'])
def login_view(request):
    serializer = LoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        data = {
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "refresh_token": str(refresh),
            "access_token": str(refresh.access_token)
        }

        # إضافة seller إذا كان موجود
        if hasattr(user, 'seller'):
            seller = user.seller
            data["seller"] = {
                "country": seller.country.name,
                "country_id": seller.country.id,
                "description": seller.description,
                "whatsapp": seller.whatsapp
            }

        return Response(data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


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

        # حفظ بيانات المستخدم مؤقتاً
        redis_client.setex(
            f"pending_user_{email}",
            300,
            json.dumps({
                "full_name": data['full_name'],
                "email": email,
                "password": data['password'],
                "whatsapp": data['whatsapp'],
                "country": data['country'].id
            })
        )

        # حفظ OTP
        redis_client.setex(f"otp_{email}", 300, hashed_otp)

        # إرسال البريد مع حماية من الأخطاء
        try:
            send_otp_email(email, otp_code)
        except Exception as e:
            print("Email sending failed:", e)
            return Response(
                {"error": "Failed to send verification email"},
                status=500
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

    # 1. إنشاء المستخدم الأساسي
    user = User.objects.create_user(
        full_name=user_data['full_name'],
        email=user_data['email'],
        password=user_data['password']
    )

    # تأكد من تعيين الدور (role) إذا كان مطلوباً
    # user.role = user_data.get('role', 'seller')
    # user.save()

    # 2. إنشاء ملف البائع (Seller) وربطه بالمستخدم
    # نفترض هنا أن user_data القادمة من Redis تحتوي على whatsapp و country
    if 'whatsapp' in user_data and 'country' in user_data:
        country_obj = get_object_or_404(Country, id=user_data['country'])

        Seller.objects.create(
            user=user,
            whatsapp=user_data['whatsapp'],
            country=country_obj,
            description=user_data.get('description', '')  # في حال كان هناك وصف
        )

    # 3. تنظيف Redis
    redis_client.delete(f"otp_{email}")
    redis_client.delete(f"pending_user_{email}")
    redis_client.delete(attempts_key)

    # 4. إصدار الـ Tokens
    refresh = RefreshToken.for_user(user)

    response_data = {
        "full_name": user.full_name,
        "email": user.email,
        "role": getattr(user, 'role', 'seller'),  # تجنب الخطأ لو لم يكن حقل role موجوداً مباشرة
        "refresh_token": str(refresh),
        "access_token": str(refresh.access_token)
    }

    # إضافة seller الآن ستعمل لأننا قمنا بإنشائه في الخطوة 2
    if hasattr(user, "seller"):
        seller = user.seller
        response_data["seller"] = {
            "country_id": seller.country.id,
            "country": seller.country.name,
            "description": seller.description,
            "whatsapp": seller.whatsapp
        }

    return Response(response_data)


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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Re-fetch with full related data so seller + price_usd are populated
        full_instance = Announcement.objects.select_related(
            "seller__user",
            "seller__country",
            "category"
        ).get(id=serializer.instance.id)

        full_serializer = self.get_serializer(full_instance)

        return Response({
            "message": "Announcement created successfully",
            "data": full_serializer.data
        }, status=status.HTTP_201_CREATED)

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



class CategoriesListView(ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Category.objects.all()

class SellerEditProfileView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerEditProfileSerializer
    http_method_names = ["patch"]

    def get_object(self):
        try:
            return Seller.objects.select_related("user").get(user=self.request.user)
        except Seller.DoesNotExist:
            raise NotFound({"detail": "Seller profile not found"})

    def update(self, request, *args, **kwargs):
        seller = self.get_object()
        serializer = self.get_serializer(seller, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "message": "Profile updated successfully",
            "data": serializer.data
        })
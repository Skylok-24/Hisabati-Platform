from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework_simplejwt.tokens import RefreshToken
from serializers import RegisterSerializer , LoginSerializer
import requests
from trusthandle_app.serializers import GoogleLoginSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


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
def register(request) :
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid() :
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response({
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "refresh_token": str(refresh),
            "access_token": str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

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


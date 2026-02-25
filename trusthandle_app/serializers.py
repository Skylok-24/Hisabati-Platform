from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import  authenticate
from trusthandle_app.models import Announcement , Seller , Country

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer) :

    confirm_password = serializers.CharField(write_only=True)
    class Meta :
        model = User
        fields = ['full_name','email','password','confirm_password']
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8}
        }

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise ValidationError({'password': 'Passwords do not match'})
        return data

    def validate_email(self,value):
        if User.objects.filter(email=value).exists() :
            raise ValidationError("Email Already Exist")
        return value

# class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
#     @classmethod
#     def get_token(cls, user):
#         token = super().get_token(user)
#         token['role'] = user.role
#         return token

class LoginSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            email=data['email'],
            password=data['password']
        )

        if not user:
            raise ValidationError("Invalid credentials")

        if not user.is_active:
            raise ValidationError("Account disabled")

        data['user'] = user
        return data

class GoogleLoginSerializer(serializers.Serializer) :
    id_token = serializers.CharField()


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = [
            "name",
            "currency_code",
            "currency_name",
            "rate_to_usd",
        ]

class SellerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    country = CountrySerializer(read_only=True)

    class Meta:
        model = Seller
        fields = [
            "email",
            "description",
            "whatsapp",
            "country",
        ]

class AnnouncementSerializer(serializers.ModelSerializer):
    seller = SellerSerializer(read_only=True)
    category = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "description",
            "price_original",
            "price_usd",
            "followers",
            "account_created_at",
            "status",
            "created_at",
            "account_link",
            "category",
            "seller",
        ]
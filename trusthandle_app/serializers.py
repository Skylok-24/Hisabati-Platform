from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import  authenticate
from trusthandle_app.models import Announcement , Seller , Country , Category
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    whatsapp = serializers.CharField(write_only=True, required=True, max_length=20)

    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        write_only=True,
        required=True
    )

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "password", "password_confirm", "whatsapp", "country"]

    # --- التعديل هنا: التحقق من أن الواتساب غير مكرر ---
    def validate_whatsapp(self, value):
        if Seller.objects.filter(whatsapp=value).exists():
            raise serializers.ValidationError("رقم الواتساب هذا مستخدم بالفعل في حساب آخر.")
        return value
    # ---------------------------------------------------

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password": "password dont match."
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        whatsapp = validated_data.pop('whatsapp')
        country = validated_data.pop('country')

        user = User.objects.create_user(
            full_name=validated_data['full_name'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )

        Seller.objects.create(
            user=user,
            whatsapp=whatsapp,
            country=country
        )

        return user

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


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class ResetPasswordConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise ValidationError({
                "confirm_password": "Passwords do not match."
            })
        return attrs


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    reason = serializers.ChoiceField(choices=['registration', 'reset_password'], default='registration')

class CountryRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'currency_code', 'currency_name', 'rate_to_usd']

class GoogleLoginSerializer(serializers.Serializer) :
    id_token = serializers.CharField()


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = [
            "id",
            "name",
        ]

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
        ]

class SellerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    country = CountrySerializer(read_only=True)

    class Meta:
        model = Seller
        fields = [
            "user",
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


class AnnouncementUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating announcements by sellers.
    Allows modification of specific fields only.
    """
    category_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "description",
            "price_original",
            "followers",
            "account_created_at",
            "status",
            "account_link",
            "category_id",
        ]
        read_only_fields = ["id", "created_at", "price_usd"]

    def validate_status(self, value):
        """Validate that status is one of the allowed choices"""
        valid_statuses = ['active', 'sold', 'inactive']
        if value not in valid_statuses:
            raise ValidationError(f"Status must be one of {valid_statuses}")
        return value

    def validate_price_original(self, value):
        """Validate that price is positive"""
        if value <= 0:
            raise ValidationError("Price must be greater than 0")
        return value

    def update(self, instance, validated_data):
        """Update announcement with new data"""
        # Handle category_id separately since it's a nested field
        category_id = validated_data.pop('category_id', None)
        
        if category_id:
            try:
                from trusthandle_app.models import Category
                category = Category.objects.get(id=category_id)
                instance.category = category
            except Category.DoesNotExist:
                raise ValidationError({"category_id": "Category not found"})
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating announcements by sellers.
    """
    category_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Announcement
        fields = [
            "title",
            "description",
            "price_original",
            "followers",
            "account_created_at",
            "status",
            "account_link",
            "category_id",
        ]

    def validate_status(self, value):
        valid_statuses = ['active', 'sold', 'inactive']
        if value not in valid_statuses:
            raise ValidationError(f"Status must be one of {valid_statuses}")
        return value

    def validate_price_original(self, value):
        if value <= 0:
            raise ValidationError("Price must be greater than 0")
        return value

    def create(self, validated_data):
        category_id = validated_data.pop('category_id')
        try:
            from trusthandle_app.models import Category
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            raise ValidationError({"category_id": "Category not found"})

        validated_data['category'] = category
        return Announcement.objects.create(**validated_data)

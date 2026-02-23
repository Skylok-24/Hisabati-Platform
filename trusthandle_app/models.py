from django.db import models
from django.contrib.auth.models import AbstractUser
from decimal import Decimal, ROUND_HALF_UP

# Create your models here.

class User(AbstractUser) :
    username = None
    first_name = None
    last_name = None
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    ROLE_CHOICES = (
    ('seller','Seller'),
    ('admin','Admin')
    )
    role = models.CharField(max_length=20,choices=ROLE_CHOICES,default='seller')
    full_name = models.CharField(max_length=30)

    def __str__(self):
        return self.email

class Country(models.Model):
    name = models.CharField(max_length=100)
    currency_code = models.CharField(max_length=3,unique=True)
    currency_name = models.CharField(max_length=50)
    rate_to_usd = models.DecimalField(max_digits=12,decimal_places=6)

    def __str__(self):
        return f"{self.name} ({self.currency_code})"

class Seller(models.Model) :
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    description = models.TextField()
    whatsapp = models.CharField(max_length=20,unique=True)
    telegrame = models.CharField(max_length=20,unique=True)

class SystemConfig(models.Model) :
    ad_script_header = models.TextField(blank=True)
    ad_script_sidebar = models.TextField(blank=True)
    ad_script_footer = models.TextField(blank=True)
    is_ads_enabled = models.BooleanField(default=False)

class Category(models.Model) :
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

class Announcement(models.Model) :
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    category = models.ForeignKey(Category,on_delete=models.PROTECT)
    title = models.CharField(max_length=50)
    description = models.TextField()
    price_original = models.DecimalField(max_digits=10, decimal_places=2)
    price_usd = models.DecimalField(max_digits=12,decimal_places=2)
    followers = models.PositiveIntegerField()
    account_created_at = models.DateField()
    STATUS_CHOICES = (
    ('active','Active'),
    ('sold','Sold'),
    ('inactive','Inactive')
    )
    status = models.CharField(max_length=10,choices=STATUS_CHOICES,default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    account_link = models.URLField(max_length=500)

    def save(self, *args, **kwargs):
        if self.seller and self.price_original:
            rate = self.seller.country.rate_to_usd

            self.price_usd = (
                    Decimal(self.price_original) * Decimal(rate)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
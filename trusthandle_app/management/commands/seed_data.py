from django.core.management.base import BaseCommand
from trusthandle_app.models import *
from decimal import Decimal
from datetime import date
import random

class Command(BaseCommand):
    help = "Seed database with test data"

    def handle(self, *args, **kwargs):

        # Clear old data (اختياري)
        Announcement.objects.all().delete()
        Seller.objects.all().delete()
        User.objects.all().delete()
        Country.objects.all().delete()
        Category.objects.all().delete()

        # Countries
        dz = Country.objects.create(
            name="Algeria",
            currency_code="DZD",
            currency_name="Algerian Dinar",
            rate_to_usd=Decimal("0.0074")
        )

        ma = Country.objects.create(
            name="Morocco",
            currency_code="MAD",
            currency_name="Moroccan Dirham",
            rate_to_usd=Decimal("0.10")
        )

        tn = Country.objects.create(
            name="Tunisia",
            currency_code="TND",
            currency_name="Tunisian Dinar",
            rate_to_usd=Decimal("0.32")
        )

        # Categories (بدون Gaming)
        instagram = Category.objects.create(name="Instagram")
        tiktok = Category.objects.create(name="TikTok")
        youtube = Category.objects.create(name="YouTube")
        facebook = Category.objects.create(name="Facebook")

        categories = [instagram, tiktok, youtube, facebook]

        # Users + Sellers
        sellers = []
        countries = [dz, ma, tn]

        for i in range(5):
            user = User.objects.create_user(
                email=f"seller{i}@gmail.com",
                password="12345678",
                full_name=f"Seller {i}",
                role="seller"
            )

            seller = Seller.objects.create(
                user=user,
                country=random.choice(countries),
                description="Test seller account",
                whatsapp=f"21355500000{i}"
            )

            sellers.append(seller)

        # Announcements
        for i in range(30):
            Announcement.objects.create(
                seller=random.choice(sellers),
                category=random.choice(categories),
                title=f"Account {i}",
                description="Test account for marketplace",
                price_original=random.randint(1000, 100000),
                followers=random.randint(1000, 500000),
                account_created_at=date(
                    random.randint(2018, 2023),
                    random.randint(1, 12),
                    random.randint(1, 28)
                ),
                account_link=f"https://example.com/account{i}"
            )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
import requests
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from trusthandle_app.models import Country


class Command(BaseCommand):
    help = "Update currency exchange rates (rate_to_usd) from external API"

    API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    TIMEOUT = 15  # seconds

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting exchange rates update...")

        try:
            response = requests.get(self.API_URL, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"API request failed: {e}"))
            return

        if "rates" not in data:
            self.stdout.write(self.style.ERROR("Invalid API response format"))
            return

        rates = data["rates"]

        updated_count = 0

        with transaction.atomic():
            for country in Country.objects.all():

                code = country.currency_code.upper()

                if code not in rates:
                    continue

                try:
                    # API يعطينا: 1 USD = X Currency
                    # نحن نريد: 1 Currency = كم USD
                    usd_to_currency = Decimal(str(rates[code]))

                    if usd_to_currency == 0:
                        continue

                    currency_to_usd = Decimal("1") / usd_to_currency

                    country.rate_to_usd = currency_to_usd
                    country.save(update_fields=["rate_to_usd"])

                    updated_count += 1

                except (InvalidOperation, ZeroDivisionError):
                    continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Exchange rates updated successfully. ({updated_count} currencies updated)"
            )
        )
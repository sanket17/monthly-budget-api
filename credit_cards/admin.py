from django.contrib import admin

from .models import CreditCard, CreditCardEntry


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "planned_amount", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "user__email")

    def get_queryset(self, request):
        # CreditCard.objects (ActiveCreditCardManager) hides soft-deleted
        # rows — admin needs to see everything for management purposes.
        return CreditCard.all_objects.all()


@admin.register(CreditCardEntry)
class CreditCardEntryAdmin(admin.ModelAdmin):
    list_display = ("description", "user", "card", "amount", "date")
    list_filter = ("date",)
    search_fields = ("description", "user__email", "card__name")

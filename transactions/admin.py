from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("description", "user", "category", "amount", "date")
    list_filter = ("category__category_type", "date")
    search_fields = ("description", "user__email", "category__name")

from django.contrib import admin

from .models import InitialBalance, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("description", "user", "category", "amount", "date")
    list_filter = ("category__category_type", "date")
    search_fields = ("description", "user__email", "category__name")


@admin.register(InitialBalance)
class InitialBalanceAdmin(admin.ModelAdmin):
    list_display = ("user", "balance_type", "amount", "effective_month")
    list_filter = ("balance_type",)
    search_fields = ("user__email",)

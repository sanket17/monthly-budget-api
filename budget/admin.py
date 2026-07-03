from django.contrib import admin

from .models import Category, PlannedAmount


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "category_type", "group", "is_active")
    list_filter = ("category_type", "group", "is_active")
    search_fields = ("name", "user__email")

    def get_queryset(self, request):
        # Category.objects (ActiveCategoryManager) hides soft-deleted rows —
        # admin needs to see everything for management purposes.
        return Category.all_objects.all()


@admin.register(PlannedAmount)
class PlannedAmountAdmin(admin.ModelAdmin):
    list_display = ("category", "user", "amount", "effective_from", "created_at")
    list_filter = ("effective_from",)
    search_fields = ("category__name", "user__email")

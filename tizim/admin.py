from django.contrib import admin

from .models import Bank, Transaction, UserProfile


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
	list_display = ("name", "address", "established_date")
	search_fields = ("name", "address")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ("user", "balance", "is_face_verified", "updated_at")
	list_filter = ("is_face_verified",)
	search_fields = ("user__username", "user__email")
	readonly_fields = ("created_at", "updated_at")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
	list_display = (
		"user",
		"amount",
		"transaction_type",
		"counterparty",
		"performed_by",
		"created_at",
	)
	list_filter = ("transaction_type", "created_at")
	search_fields = ("user__email", "counterparty")
	autocomplete_fields = ("user", "performed_by")
	date_hierarchy = "created_at"
from django.contrib import admin
from .models import (
    UserProfile,
    Account,
    Category,
    Receipt,
    ReceiptItem,
    Transaction,
    Budget,
    RecurringRule,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'clerk_user_id', 'email', 'first_name', 'last_name', 'created_at')
    search_fields = ('clerk_user_id', 'email', 'first_name', 'last_name')
    list_filter = ('created_at',)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'account_type', 'is_active', 'created_at')
    list_filter = ('account_type', 'is_active')
    search_fields = ('name', 'institution_name', 'user__email', 'user__clerk_user_id')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'is_system_default', 'user', 'icon_name', 'color_hex')
    list_filter = ('category_type', 'is_system_default')
    search_fields = ('name',)


class ReceiptItemInline(admin.TabularInline):
    model = ReceiptItem
    extra = 1


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('merchant_name', 'user', 'total_amount', 'receipt_date', 'ocr_status', 'created_at')
    list_filter = ('ocr_status', 'receipt_date')
    search_fields = ('merchant_name', 'invoice_number', 'user__email')
    inlines = [ReceiptItemInline]


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'receipt', 'quantity', 'unit_price', 'total_price', 'category')
    search_fields = ('item_name', 'receipt__merchant_name')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'transaction_type', 'amount', 'account', 'category', 'transaction_date', 'source', 'status')
    list_filter = ('transaction_type', 'source', 'status', 'transaction_date')
    search_fields = ('title', 'notes', 'user__email')
    date_hierarchy = 'transaction_date'


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category', 'period_type', 'amount_limit', 'start_date', 'end_date', 'is_active')
    list_filter = ('period_type', 'is_active')
    search_fields = ('name', 'user__email')


@admin.register(RecurringRule)
class RecurringRuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'transaction_type', 'amount', 'frequency', 'next_run_date', 'is_active')
    list_filter = ('frequency', 'transaction_type', 'is_active')
    search_fields = ('title', 'user__email')



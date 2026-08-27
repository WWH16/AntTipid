from django.db import models


class UserProfile(models.Model):
    """
    User Profile associated with Clerk authentication.
    """
    id = models.BigAutoField(primary_key=True)
    clerk_user_id = models.CharField(max_length=255, unique=True, db_index=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, default='')
    last_name = models.CharField(max_length=150, blank=True, default='')
    avatar_url = models.URLField(max_length=1000, blank=True, null=True)
    monthly_income_target = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    theme_preference = models.CharField(max_length=20, default='system')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email or self.clerk_user_id


class Account(models.Model):
    """
    Financial Account or Wallet (Cash Wallet, GCash, Maya, Bank Accounts, Credit Cards).
    """
    class AccountType(models.TextChoices):
        CASH = 'CASH', 'Cash Wallet'
        E_WALLET = 'E_WALLET', 'E-Wallet (GCash / Maya)'
        BANK_ACCOUNT = 'BANK_ACCOUNT', 'Bank Account'
        CREDIT_CARD = 'CREDIT_CARD', 'Credit Card'
        SAVINGS = 'SAVINGS', 'Savings Account'
        OTHER = 'OTHER', 'Other'

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='accounts', db_index=True)
    name = models.CharField(max_length=100, help_text="e.g. Cash Wallet, GCash, BPI Checking")
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.CASH)
    institution_name = models.CharField(max_length=100, blank=True, default='', help_text="e.g. GCash, Maya, BPI, BDO, Cash")
    account_number_mask = models.CharField(max_length=30, blank=True, default='', help_text="e.g. •••• 4210")
    color_hex = models.CharField(max_length=10, default='#163300')
    icon = models.CharField(max_length=50, default='account_balance_wallet')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Account / Wallet'
        verbose_name_plural = 'Accounts & Wallets'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"


class Category(models.Model):
    """
    Income and Expense Spending Categories.
    """
    class CategoryType(models.TextChoices):
        EXPENSE = 'EXPENSE', 'Expense'
        INCOME = 'INCOME', 'Income'

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='categories', null=True, blank=True, help_text="Null for system-default categories")
    parent_category = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    name = models.CharField(max_length=80)
    category_type = models.CharField(max_length=10, choices=CategoryType.choices, default=CategoryType.EXPENSE)
    icon_name = models.CharField(max_length=50, default='category', help_text="Material symbols icon key")
    color_hex = models.CharField(max_length=10, default='#5C8F3A')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"


class Receipt(models.Model):
    """
    Uploaded receipt processed with Gemini Vision OCR.
    """
    class OCRStatus(models.TextChoices):
        PROCESSING = 'PROCESSING', 'Processing'
        SUCCESS = 'SUCCESS', 'Success'
        EDITED = 'EDITED', 'Edited'
        FAILED = 'FAILED', 'Failed'

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='receipts', db_index=True)
    image = models.ImageField(upload_to='receipts/%Y/%m/', blank=True, null=True)
    image_url = models.TextField(blank=True, null=True, help_text="Public image URL or Data URI fallback for serverless deployments")
    merchant_name = models.CharField(max_length=200, blank=True, default='')
    merchant_address = models.TextField(blank=True, default='')
    receipt_date = models.DateField(null=True, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True, default='')
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    gemini_raw_json = models.JSONField(blank=True, null=True, help_text="Raw structured JSON returned by Gemini OCR")
    ocr_status = models.CharField(max_length=20, choices=OCRStatus.choices, default=OCRStatus.PROCESSING)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.95)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Receipt'
        verbose_name_plural = 'Receipts'
        ordering = ['-receipt_date', '-created_at']

    def __str__(self):
        return f"{self.merchant_name or 'Receipt'} - ₱{self.total_amount:,.2f} ({self.receipt_date or 'No Date'})"


class ReceiptItem(models.Model):
    """
    Individual extracted or edited line items from a scanned receipt.
    """
    id = models.BigAutoField(primary_key=True)
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='receipt_items')
    item_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1.00)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Receipt Line Item'
        verbose_name_plural = 'Receipt Line Items'
        ordering = ['id']

    def __str__(self):
        return f"{self.item_name} x{self.quantity} = ₱{self.total_price:,.2f}"


class Transaction(models.Model):
    """
    Financial Ledger transaction (Expense, Income, or Account-to-Account Transfer).
    """
    class TransactionType(models.TextChoices):
        EXPENSE = 'EXPENSE', 'Expense'
        INCOME = 'INCOME', 'Income'
        TRANSFER = 'TRANSFER', 'Transfer'

    class SourceType(models.TextChoices):
        MANUAL = 'MANUAL', 'Manual Entry'
        OCR_SCAN = 'OCR_SCAN', 'Receipt Scan'
        RECURRING = 'RECURRING', 'Recurring Schedule'

    class Status(models.TextChoices):
        CLEARED = 'CLEARED', 'Cleared'
        PENDING = 'PENDING', 'Pending'
        RECONCILED = 'RECONCILED', 'Reconciled'

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='transactions', db_index=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='source_transactions', help_text="Source Account (e.g. Cash Wallet, GCash, Bank)")
    destination_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='destination_transactions', help_text="Target Account for Transfers")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    receipt = models.OneToOneField(Receipt, on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_transaction')
    transaction_type = models.CharField(max_length=15, choices=TransactionType.choices, default=TransactionType.EXPENSE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    title = models.CharField(max_length=200, help_text="Merchant name or transaction description")
    transaction_date = models.DateField(db_index=True)
    notes = models.TextField(blank=True, default='')
    source = models.CharField(max_length=15, choices=SourceType.choices, default=SourceType.MANUAL)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.CLEARED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"[{self.get_transaction_type_display()}] {self.title} - ₱{self.amount:,.2f} ({self.transaction_date})"


class Budget(models.Model):
    """
    Category-based or overall monthly spending budgets.
    """
    class PeriodType(models.TextChoices):
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'
        YEARLY = 'YEARLY', 'Yearly'

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='budgets', db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='budgets', help_text="Leave empty for Overall Monthly Budget")
    name = models.CharField(max_length=100, help_text="e.g. Food & Dining Budget, November Limit")
    period_type = models.CharField(max_length=10, choices=PeriodType.choices, default=PeriodType.MONTHLY)
    amount_limit = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    warning_threshold_pct = models.PositiveIntegerField(default=80, help_text="Trigger alert at percentage of budget spent (e.g. 80%)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Budget'
        verbose_name_plural = 'Budgets'
        ordering = ['-start_date', 'name']

    def __str__(self):
        cat_name = self.category.name if self.category else "Overall"
        return f"{self.name} ({cat_name}) - Limit: ₱{self.amount_limit:,.2f}"


class RecurringRule(models.Model):
    """
    Recurring transaction templates (rent, subscriptions, salary).
    """
    class Frequency(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        BIWEEKLY = 'BIWEEKLY', 'Bi-Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'
        YEARLY = 'YEARLY', 'Yearly'

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='recurring_rules', db_index=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='recurring_rules')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='recurring_rules')
    title = models.CharField(max_length=200, help_text="e.g. Netflix, House Rent, Salary")
    transaction_type = models.CharField(max_length=15, choices=Transaction.TransactionType.choices, default=Transaction.TransactionType.EXPENSE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=15, choices=Frequency.choices, default=Frequency.MONTHLY)
    start_date = models.DateField()
    next_run_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Recurring Rule'
        verbose_name_plural = 'Recurring Rules'
        ordering = ['next_run_date']

    def __str__(self):
        return f"{self.title} ({self.get_frequency_display()}) - ₱{self.amount:,.2f}"


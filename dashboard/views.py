import os
import json
import base64
import uuid
from io import BytesIO
from PIL import Image as PILImage
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.db import transaction as db_transaction
from django.core.files.base import ContentFile

from .models import (
    UserProfile,
    Account,
    Category,
    Transaction,
    Receipt,
    ReceiptItem,
    Budget,
    RecurringRule,
)
from .services import (
    get_current_user_profile,
    get_dashboard_data,
    get_transactions_data,
    get_budget_data,
    get_reports_data,
)


def landing_view(request):
    """Render the AntTipid Landing Page."""
    context = {
        'active_nav': 'landing',
    }
    return render(request, 'dashboard/landing.html', context)


def dashboard_view(request):
    """Render the main AntTipid dashboard with live database stats."""
    profile = get_current_user_profile(request)
    data = get_dashboard_data(profile) if profile else {}

    context = {
        'active_nav': 'dashboard',
        'profile': profile,
        **data,
    }
    return render(request, 'dashboard/index.html', context)


def transactions_view(request):
    """Render the transactions history view with database data and filtering."""
    profile = get_current_user_profile(request)
    data = get_transactions_data(profile, request.GET) if profile else {}

    context = {
        'active_nav': 'transactions',
        'profile': profile,
        'selected_type': request.GET.get('type', ''),
        'selected_category': request.GET.get('category', ''),
        'search_query': request.GET.get('q', ''),
        **data,
    }
    return render(request, 'dashboard/transactions.html', context)


def budget_view(request):
    """Render the budget view with live spending against category targets."""
    profile = get_current_user_profile(request)
    selected_month = request.GET.get('month')
    data = get_budget_data(profile, selected_month=selected_month) if profile else {}

    context = {
        'active_nav': 'budgets',
        'profile': profile,
        **data,
    }
    return render(request, 'dashboard/budget.html', context)


def reports_view(request):
    """Render the financial reports and insights view backed by database calculations."""
    profile = get_current_user_profile(request)
    period_data = get_reports_data(profile) if profile else {}

    context = {
        'active_nav': 'reports',
        'profile': profile,
        'period_data_json': json.dumps(period_data),
    }
    return render(request, 'dashboard/reports.html', context)


def receipt_detail_view(request, pk=None):
    """Render the receipt details view with database line items."""
    profile = get_current_user_profile(request)
    receipt = None
    if pk:
        receipt = get_object_or_404(Receipt, id=pk, user=profile)
    elif profile:
        receipt = Receipt.objects.filter(user=profile).prefetch_related('items').order_by('-receipt_date', '-created_at').first()

    categories = Category.objects.filter(user=profile).order_by('name') if profile else []
    accounts = Account.objects.filter(user=profile, is_active=True).order_by('name') if profile else []

    items = receipt.items.all() if receipt else []
    items_list = []
    for itm in items:
        items_list.append({
            'id': str(itm.id),
            'description': itm.item_name,
            'qty': int(itm.quantity) if itm.quantity == int(itm.quantity) else float(itm.quantity),
            'unitPrice': float(itm.unit_price),
            'totalPrice': float(itm.total_price),
        })

    context = {
        'active_nav': 'transactions',
        'profile': profile,
        'receipt': receipt,
        'items': items,
        'items_json': json.dumps(items_list),
        'categories': categories,
        'accounts': accounts,
    }
    return render(request, 'dashboard/receipt_detail.html', context)


def transaction_detail_view(request, pk=None):
    """Render the transaction details view matching receipt details styling."""
    profile = get_current_user_profile(request)
    transaction = None
    if pk:
        transaction = get_object_or_404(Transaction, id=pk, user=profile)
    elif profile:
        transaction = Transaction.objects.filter(user=profile).order_by('-transaction_date', '-created_at').first()

    if not transaction and profile:
        return redirect('transactions')

    categories = Category.objects.filter(user=profile).order_by('name') if profile else []
    accounts = Account.objects.filter(user=profile, is_active=True).order_by('name') if profile else []

    context = {
        'active_nav': 'transactions',
        'profile': profile,
        'transaction': transaction,
        'categories': categories,
        'accounts': accounts,
    }
    return render(request, 'dashboard/transaction_detail.html', context)


def add_transaction_view(request):
    """Render and process the manual transaction entry screen."""
    profile = get_current_user_profile(request)

    if request.method == 'POST':
        try:
            amount_str = request.POST.get('amount', '0').replace('₱', '').replace(',', '').strip()
            amount = Decimal(amount_str)
            title = request.POST.get('title', '').strip() or 'Untitled Transaction'
            tx_type = request.POST.get('type', 'expense').upper()
            category_name = request.POST.get('category', '').strip()
            account_name = request.POST.get('account', 'Cash Wallet').strip()
            tx_date_str = request.POST.get('date', '').strip()
            notes = request.POST.get('notes', '').strip()

            tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d').date() if tx_date_str else date.today()

            # Resolve Account
            account = Account.objects.filter(user=profile, name__icontains=account_name.split()[0]).first()
            if not account:
                account = Account.objects.filter(user=profile, account_type=Account.AccountType.CASH).first()

            # Resolve Category
            category = None
            if category_name:
                category = Category.objects.filter(user=profile, name__iexact=category_name).first()
                if not category:
                    category = Category.objects.create(
                        user=profile,
                        name=category_name,
                        category_type=Category.CategoryType.INCOME if tx_type == 'INCOME' else Category.CategoryType.EXPENSE,
                        icon_name='payments' if tx_type == 'INCOME' else 'shopping_bag',
                        color_hex='#5C8F3A'
                    )

            with db_transaction.atomic():
                tx = Transaction.objects.create(
                    user=profile,
                    account=account,
                    category=category,
                    transaction_type=tx_type if tx_type in ('EXPENSE', 'INCOME', 'TRANSFER') else 'EXPENSE',
                    amount=amount,
                    title=title,
                    transaction_date=tx_date,
                    notes=notes,
                    source=Transaction.SourceType.MANUAL,
                )

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'id': str(tx.id)})
            return redirect('transactions')

        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)

    categories = Category.objects.filter(user=profile).order_by('name') if profile else []
    accounts = Account.objects.filter(user=profile, is_active=True).order_by('name') if profile else []

    context = {
        'active_nav': 'add_transaction',
        'profile': profile,
        'categories': categories,
        'accounts': accounts,
    }
    return render(request, 'dashboard/add_transaction.html', context)


def scan_receipt_view(request):
    """Render the AI Receipt Scanner & Editor screen."""
    profile = get_current_user_profile(request)
    categories = Category.objects.filter(user=profile, category_type=Category.CategoryType.EXPENSE).order_by('name') if profile else []
    accounts = Account.objects.filter(user=profile, is_active=True).order_by('name') if profile else []

    context = {
        'active_nav': 'scan_receipt',
        'profile': profile,
        'categories': categories,
        'accounts': accounts,
        'has_gemini_key': bool(os.getenv('GEMINI_API_KEY')),
    }
    return render(request, 'dashboard/scan_receipt.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
# JSON API ENDPOINTS FOR CLIENT-SIDE ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_POST
def api_create_transaction(request):
    """API endpoint to create a new manual transaction."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        amount = Decimal(str(data.get('amount', 0)))
        title = data.get('title', '').strip() or 'Untitled Transaction'
        tx_type = data.get('type', 'expense').upper()
        category_name = data.get('category', '').strip()
        account_name = data.get('account', 'Cash').strip()
        tx_date_str = data.get('date', '').strip()
        notes = data.get('notes', '').strip()

        tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d').date() if tx_date_str else date.today()

        account = Account.objects.filter(user=profile, name__icontains=account_name.split()[0]).first()
        if not account:
            account = Account.objects.filter(user=profile, account_type=Account.AccountType.CASH).first()

        category = Category.objects.filter(user=profile, name__icontains=category_name).first() if category_name else None

        with db_transaction.atomic():
            tx = Transaction.objects.create(
                user=profile,
                account=account,
                category=category,
                transaction_type=tx_type if tx_type in ('EXPENSE', 'INCOME', 'TRANSFER') else 'EXPENSE',
                amount=amount,
                title=title,
                transaction_date=tx_date,
                notes=notes,
                source=Transaction.SourceType.MANUAL,
            )

        return JsonResponse({'success': True, 'id': str(tx.id)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_update_transaction(request, pk):
    """API endpoint to update an existing transaction."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tx = get_object_or_404(Transaction, id=pk, user=profile)

    try:
        data = json.loads(request.body.decode('utf-8'))
        if 'amount' in data:
            tx.amount = Decimal(str(data['amount']))

        if 'type' in data and data['type']:
            t_type = data['type'].strip().upper()
            if t_type in ('EXPENSE', 'INCOME', 'TRANSFER'):
                tx.transaction_type = t_type

        if 'title' in data:
            tx.title = data['title'].strip()
        if 'notes' in data:
            tx.notes = data['notes'].strip()
        if 'date' in data and data['date']:
            tx.transaction_date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        if 'category' in data and data['category']:
            cat_name = data['category'].strip()
            cat = Category.objects.filter(user=profile, name__iexact=cat_name).first()
            if not cat:
                cat = Category.objects.create(
                    user=profile,
                    name=cat_name,
                    category_type=Category.CategoryType.INCOME if tx.transaction_type == 'INCOME' else Category.CategoryType.EXPENSE,
                    icon_name='payments' if tx.transaction_type == 'INCOME' else 'shopping_bag',
                    color_hex='#5C8F3A'
                )
            tx.category = cat

        if 'account' in data and data['account']:
            acc = Account.objects.filter(user=profile, name__icontains=data['account'].split()[0]).first()
            if acc and acc != tx.account:
                tx.account = acc

        tx.save()
        return JsonResponse({'success': True, 'id': str(tx.id)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_delete_transaction(request, pk):
    """API endpoint to delete a transaction."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    tx = get_object_or_404(Transaction, id=pk, user=profile)
    tx.delete()

    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def api_save_budget(request):
    """API endpoint to create or update category budget limits."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        category_id = data.get('category_id')
        category_name = data.get('category')
        amount_limit = Decimal(str(data.get('amount_limit') or data.get('amount') or 0))

        today = date.today()
        start_of_month = today.replace(day=1)
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        category_icon = data.get('icon') or data.get('icon_name') or 'category'
        category_color = data.get('color') or data.get('color_hex') or '#5C8F3A'

        if category_id:
            category = Category.objects.filter(id=category_id, user=profile).first()
            if category:
                if category_name and category_name.strip():
                    category.name = category_name.strip()
                if data.get('icon'):
                    category.icon_name = data.get('icon')
                if data.get('color'):
                    category.color_hex = data.get('color')
                category.save()
        elif category_name:
            category = Category.objects.filter(name__iexact=category_name, user=profile).first()
            if not category:
                category = Category.objects.create(
                    user=profile,
                    name=category_name,
                    category_type=Category.CategoryType.EXPENSE,
                    icon_name=category_icon,
                    color_hex=category_color
                )
            elif data.get('icon') or data.get('color'):
                if data.get('icon'):
                    category.icon_name = data.get('icon')
                if data.get('color'):
                    category.color_hex = data.get('color')
                category.save()
        else:
            category = None

        has_budget = data.get('has_budget')
        if has_budget is None:
            has_budget = (amount_limit > 0)

        if not has_budget or amount_limit <= 0:
            if category:
                Budget.objects.filter(user=profile, category=category).delete()
            return JsonResponse({'success': True, 'unbudgeted': True})

        budget, created = Budget.objects.update_or_create(
            user=profile,
            category=category,
            period_type=Budget.PeriodType.MONTHLY,
            defaults={
                'name': f"{category.name} Budget" if category else 'Overall Monthly Budget',
                'amount_limit': amount_limit,
                'start_date': start_of_month,
                'end_date': end_of_month,
                'is_active': True,
            }
        )

        return JsonResponse({'success': True, 'id': str(budget.id)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_update_receipt_items(request, pk):
    """API endpoint to update line items for a receipt."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    receipt = get_object_or_404(Receipt, id=pk, user=profile)

    try:
        data = json.loads(request.body.decode('utf-8'))
        items_data = data.get('items', [])

        with db_transaction.atomic():
            receipt.items.all().delete()
            new_total = Decimal('0.00')

            for item in items_data:
                item_name = (item.get('name') or item.get('description') or '').strip() or 'Item'
                qty = Decimal(str(item.get('qty', 1)))
                unit_price = Decimal(str(item.get('price') or item.get('unitPrice') or 0))
                total_price = qty * unit_price
                new_total += total_price

                ReceiptItem.objects.create(
                    receipt=receipt,
                    item_name=item_name,
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=total_price,
                )

            receipt.total_amount = new_total
            receipt.ocr_status = Receipt.OCRStatus.EDITED
            receipt.save(update_fields=['total_amount', 'ocr_status', 'updated_at'])

            # If linked transaction exists, update its amount too
            if hasattr(receipt, 'linked_transaction') and receipt.linked_transaction:
                tx = receipt.linked_transaction
                tx.amount = new_total
                tx.save(update_fields=['amount', 'updated_at'])

        return JsonResponse({'success': True, 'total': float(new_total)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_delete_receipt(request, pk):
    """API endpoint to delete a scanned receipt."""
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    receipt = get_object_or_404(Receipt, id=pk, user=profile)
    receipt.delete()
    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def api_save_scanned_receipt(request):
    """
    Directly saves a scanned receipt as an Expense Transaction with linked Receipt and ReceiptItems.
    Compresses receipt image before storing in the database to optimize storage.
    """
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        merchant = data.get('merchant', '').strip() or 'Receipt Expense'
        total = Decimal(str(data.get('total', 0)))
        tax = Decimal(str(data.get('tax', 0)))
        date_str = data.get('date', '').strip()
        category_name = data.get('category', '').strip()
        payment_method = data.get('payment_method', 'CASH').strip()
        items_data = data.get('items', [])
        notes = data.get('notes', '').strip()
        image_data = data.get('image_data', '').strip()

        tx_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()

        # Find or create account / payment method
        account = None
        if payment_method:
            account = Account.objects.filter(user=profile, name__iexact=payment_method).first()
            if not account:
                account = Account.objects.filter(user=profile, name__icontains=payment_method.split()[0]).first()
            if not account:
                pm_lower = payment_method.lower()
                if 'gcash' in pm_lower or 'maya' in pm_lower or 'wallet' in pm_lower:
                    account = Account.objects.filter(user=profile, account_type=Account.AccountType.E_WALLET).first()
                elif 'card' in pm_lower or 'visa' in pm_lower or 'master' in pm_lower:
                    account = Account.objects.filter(user=profile, account_type__in=[Account.AccountType.CREDIT_CARD, Account.AccountType.BANK_ACCOUNT]).first()
            
            # If still not found and a custom payment method was detected, auto-create the new Account for the user!
            if not account and payment_method.strip().upper() not in ('OTHER', 'UNKNOWN'):
                pm_name = payment_method.strip().title()
                pm_upper = payment_method.upper()
                acc_type = Account.AccountType.CASH
                acc_icon = 'payments'
                acc_color = '#5C8F3A'
                if any(w in pm_upper for w in ['GCASH', 'MAYA', 'WALLET', 'PAY', 'SHOPEE', 'GRAB']):
                    acc_type = Account.AccountType.E_WALLET
                    acc_icon = 'account_balance_wallet'
                    acc_color = '#005CEE'
                elif any(w in pm_upper for w in ['CARD', 'VISA', 'MASTER', 'AMEX', 'DEBIT', 'CREDIT']):
                    acc_type = Account.AccountType.CREDIT_CARD
                    acc_icon = 'credit_card'
                    acc_color = '#D97706'
                elif any(w in pm_upper for w in ['BANK', 'TRANSFER', 'INSTAPAY', 'PESONET', 'BDO', 'BPI', 'UB', 'METROBANK']):
                    acc_type = Account.AccountType.BANK_ACCOUNT
                    acc_icon = 'account_balance'
                    acc_color = '#8B5CF6'

                account = Account.objects.create(
                    user=profile,
                    name=pm_name,
                    account_type=acc_type,
                    institution_name=pm_name,
                    color_hex=acc_color,
                    icon=acc_icon,
                )

        if not account:
            account = Account.objects.filter(user=profile, is_active=True).first()
            if not account:
                account = Account.objects.create(user=profile, name='Cash Wallet', account_type=Account.AccountType.CASH)

        # Find or create category if it was newly suggested
        category = None
        if category_name:
            category = Category.objects.filter(user=profile, name__iexact=category_name).first()
            if not category:
                category = Category.objects.filter(user=profile, name__icontains=category_name).first()
            if not category:
                lower_cat = category_name.lower()
                cat_icon = 'category'
                if any(w in lower_cat for w in ['pet', 'vet', 'dog', 'cat']):
                    cat_icon = 'pets'
                elif any(w in lower_cat for w in ['pharmacy', 'med', 'drug', 'health', 'hospital', 'doctor']):
                    cat_icon = 'local_hospital'
                elif any(w in lower_cat for w in ['grocer', 'market', 'supermarket']):
                    cat_icon = 'local_grocery_store'
                elif any(w in lower_cat for w in ['food', 'din', 'restau', 'cafe', 'snack']):
                    cat_icon = 'restaurant'
                elif any(w in lower_cat for w in ['coffee', 'starbucks', 'tea']):
                    cat_icon = 'coffee'
                elif any(w in lower_cat for w in ['trans', 'gas', 'fuel', 'grab', 'taxi', 'car']):
                    cat_icon = 'directions_car'
                elif any(w in lower_cat for w in ['util', 'electric', 'water', 'power', 'bill']):
                    cat_icon = 'bolt'
                elif any(w in lower_cat for w in ['tech', 'gadget', 'phone', 'device', 'elec']):
                    cat_icon = 'devices'
                elif any(w in lower_cat for w in ['cloth', 'apparel', 'shop', 'mall']):
                    cat_icon = 'shopping_bag'
                elif any(w in lower_cat for w in ['movie', 'cinema', 'game', 'entertain']):
                    cat_icon = 'movie'
                elif any(w in lower_cat for w in ['gym', 'fit', 'sport']):
                    cat_icon = 'fitness_center'

                category = Category.objects.create(
                    user=profile,
                    name=category_name,
                    category_type=Category.CategoryType.EXPENSE,
                    icon_name=cat_icon,
                    color_hex='#5C8F3A'
                )

        # Image compression & storage
        image_file = None
        if image_data:
            try:
                raw_b64 = image_data.split(',', 1)[1] if ',' in image_data else image_data
                img_bytes = base64.b64decode(raw_b64)
                pil_img = PILImage.open(BytesIO(img_bytes))
                if pil_img.mode in ('RGBA', 'P'):
                    pil_img = pil_img.convert('RGB')
                
                # Maximum dimension 1400px for optimal storage savings
                max_dim = 1400
                if pil_img.width > max_dim or pil_img.height > max_dim:
                    pil_img.thumbnail((max_dim, max_dim), PILImage.Resampling.LANCZOS)
                
                out_buf = BytesIO()
                pil_img.save(out_buf, format='JPEG', quality=75, optimize=True)
                file_name = f"receipt_{tx_date}_{uuid.uuid4().hex[:6]}.jpg"
                image_file = ContentFile(out_buf.getvalue(), name=file_name)
            except Exception as img_err:
                print("Receipt image compression notice:", img_err)

        with db_transaction.atomic():
            receipt = Receipt.objects.create(
                user=profile,
                image=image_file,
                merchant_name=merchant,
                receipt_date=tx_date,
                subtotal_amount=total - tax if total >= tax else total,
                tax_amount=tax,
                total_amount=total,
                ocr_status=Receipt.OCRStatus.SUCCESS,
                gemini_raw_json=data,
            )

            for item in items_data:
                desc = item.get('description', '').strip() or 'Item'
                qty = Decimal(str(item.get('quantity', 1)))
                price = Decimal(str(item.get('price', 0)))
                item_total = price * qty if price else Decimal('0.00')
                ReceiptItem.objects.create(
                    receipt=receipt,
                    item_name=desc,
                    quantity=qty,
                    unit_price=price,
                    total_price=item_total,
                )

            if not notes and items_data:
                notes = f"{len(items_data)} items scanned from receipt ({merchant})"

            tx = Transaction.objects.create(
                user=profile,
                account=account,
                category=category,
                receipt=receipt,
                transaction_type=Transaction.TransactionType.EXPENSE,
                amount=total,
                title=merchant,
                transaction_date=tx_date,
                notes=notes,
                source=Transaction.SourceType.OCR_SCAN,
                status=Transaction.Status.CLEARED,
            )

        return JsonResponse({
            'success': True,
            'transaction_id': str(tx.id),
            'receipt_id': str(receipt.id),
            'redirect_url': '/transactions/'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
def api_scan_receipt_view(request):
    """
    API Endpoint for processing receipt images with Gemini API OCR.
    Receives image upload or sample request, calls Gemini Vision API,
    and returns itemized JSON.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    profile = get_current_user_profile(request)
    gemini_key = NONE
    image_base64 = None
    mime_type = 'image/jpeg'

    if request.FILES.get('receipt_image'):
        uploaded_file = request.FILES['receipt_image']
        image_bytes = uploaded_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        if uploaded_file.content_type:
            mime_type = uploaded_file.content_type
    else:
        try:
            raw_body = request.body
            if raw_body:
                payload = json.loads(raw_body)
                raw_data = payload.get('image_data', '')
                if ',' in raw_data:
                    header, raw_data = raw_data.split(',', 1)
                    if 'png' in header:
                        mime_type = 'image/png'
                    elif 'webp' in header:
                        mime_type = 'image/webp'
                image_base64 = raw_data
        except Exception:
            pass

    if not gemini_key:
        return JsonResponse({
            'error': 'Gemini API key is not configured. Please configure GEMINI_API_KEY in your environment or record the transaction manually.',
            'error_type': 'missing_api_key'
        }, status=400)

    if not image_base64 and 'image_bytes' not in locals():
        return JsonResponse({
            'error': 'No receipt image provided. Please upload or capture an image.',
            'error_type': 'missing_image'
        }, status=400)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=gemini_key,
            http_options=types.HttpOptions(timeout=25_000),
        )
        user_cat_names = list(Category.objects.filter(user=profile).values_list('name', flat=True)) if profile else []
        if user_cat_names:
            category_guideline = f"5. Category: Choose the best matching category from the user's existing categories: [{', '.join(user_cat_names)}]. If the receipt items do not fit any of these, return a concise, natural category name reflecting the purchase (e.g. 'Electronics', 'Pet Supplies', 'Hardware')."
        else:
            category_guideline = "5. Category: Return a concise, natural category name reflecting the receipt purchase (e.g. 'Groceries', 'Food & Dining', 'Transportation', 'Utilities', 'Shopping', 'Healthcare', 'Entertainment', 'Services')."

        user_acc_names = list(Account.objects.filter(user=profile, is_active=True).values_list('name', flat=True)) if profile else []
        if user_acc_names:
            payment_guideline = (
                f"6. Payment Method: Choose the best matching account from the user's existing payment sources: [{', '.join(user_acc_names)}]. "
                "If the payment mode on the receipt is a new/unlisted payment method, return a clean uppercase keyword identifying it (e.g. 'GCASH', 'MAYA', 'CREDIT CARD', 'DEBIT CARD', 'BANK TRANSFER', 'CASH', 'SHOPEEPAY')."
            )
        else:
            payment_guideline = (
                "6. Payment Method: Extract ONLY a clean uppercase keyword identifying the payment mode used on the receipt "
                "(e.g. 'GCASH', 'MAYA', 'CREDIT CARD', 'DEBIT CARD', 'CASH', 'BANK TRANSFER'). If unclear or not indicated, return 'CASH'."
            )

        prompt_text = (
            "You are an expert receipt OCR assistant for a Philippine personal finance app (AntTipid). "
            "Analyze this receipt image and return ONLY a valid JSON object matching this exact schema without markdown wrap:\n"
            "{\n"
            '  "merchant": "Store Name",\n'
            '  "date": "YYYY-MM-DD",\n'
            '  "time": "HH:MM",\n'
            '  "category": "Groceries",\n'
            '  "payment_method": "GCASH | MAYA | CASH | CREDIT CARD | DEBIT CARD | BANK TRANSFER | OTHER",\n'
            '  "subtotal": 0.00,\n'
            '  "tax": 0.00,\n'
            '  "total": 0.00,\n'
            '  "cash_tendered": 0.00,\n'
            '  "change": 0.00,\n'
            '  "items": [\n'
            '    {"description": "Item description", "quantity": 1, "price": 0.00}\n'
            '  ]\n'
            "}\n"
            "Important guidelines:\n"
            "1. Date and Time: Extract the exact transaction date (YYYY-MM-DD) and time (24-hour HH:MM format e.g. 14:35 or 09:15) printed on the receipt. If date or time is not printed or cannot be clearly read, return null for that field.\n"
            "2. Total/Grand Total: Read the exact grand total printed on the receipt.\n"
            "3. Tax: Do NOT calculate or guess tax on your own. Only extract tax if it is explicitly printed on the receipt image; otherwise return 0.00.\n"
            "4. Cash & Change: If payment method is Cash, extract the cash tendered and change stated on the receipt; otherwise return 0.00 for both.\n"
            f"{category_guideline}\n"
            f"{payment_guideline}"
        )

        raw_bytes = image_bytes if 'image_bytes' in locals() else base64.b64decode(image_base64)

        # Cascade through candidate models starting with gemini-3.6-flash
        candidate_models = [
            "gemini-3.6-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]

        response = None
        last_model_err = None

        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(
                            data=raw_bytes,
                            mime_type=mime_type
                        ),
                        prompt_text
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json"
                    )
                )
                if response:
                    break
            except Exception as model_err:
                last_model_err = model_err
                err_lower = str(model_err).lower()
                if (
                    'not found' in err_lower
                    or 'unsupported' in err_lower
                    or '404' in err_lower
                    or 'no longer available' in err_lower
                ):
                    continue
                else:
                    raise model_err

        if not response:
            if last_model_err:
                raise last_model_err
            raise RuntimeError("Failed to generate content with available Gemini models.")

        raw_text = response.text.strip()
        if raw_text.startswith('```'):
            raw_text = raw_text.split('```')[1]
            if raw_text.startswith('json'):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        extracted = json.loads(raw_text)
        extracted['source'] = 'gemini_api'
        return JsonResponse(extracted)

    except Exception as e:
        err_str = str(e)
        err_lower = err_str.lower()
        if 'resource_exhausted' in err_lower or 'quota' in err_lower or '429' in err_lower or 'rate limit' in err_lower or 'exhausted' in err_lower:
            return JsonResponse({
                'error': 'Gemini API quota has been exhausted. You have reached your rate limit or free tier quota for receipt scanning. You can still enter or edit transaction details manually.',
                'error_type': 'quota_exceeded',
                'detail': err_str
            }, status=429)
        elif 'api_key_invalid' in err_lower or 'invalid api key' in err_lower or 'permission_denied' in err_lower or 'unauthorized' in err_lower or 'forbidden' in err_lower:
            return JsonResponse({
                'error': 'Gemini API key is invalid or unauthorized. Please verify your GEMINI_API_KEY configuration.',
                'error_type': 'auth_error',
                'detail': err_str
            }, status=401)
        else:
            return JsonResponse({
                'error': f'Receipt scanning error: {err_str}',
                'error_type': 'ocr_error',
                'detail': err_str
            }, status=500)


# ==============================================================================
# Account & Payment Method Management APIs
# ==============================================================================

@csrf_exempt
@require_http_methods(['GET'])
def api_list_accounts(request):
    """
    Returns active accounts / payment methods for current user.
    """
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    accounts = Account.objects.filter(user=profile, is_active=True).order_by('name')
    data = []
    for acc in accounts:
        data.append({
            'id': str(acc.id),
            'name': acc.name,
            'account_type': acc.account_type,
            'account_type_display': acc.get_account_type_display(),
            'icon': acc.icon or 'payments',
            'color_hex': acc.color_hex or '#163300',
        })
    return JsonResponse({'accounts': data})


@csrf_exempt
@require_http_methods(['POST'])
def api_create_account(request):
    """
    Create a new Account / Payment Method.
    """
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Account name is required.'}, status=400)

        account_type = data.get('account_type', Account.AccountType.CASH)
        if account_type not in dict(Account.AccountType.choices):
            account_type = Account.AccountType.CASH

        icon = data.get('icon', 'payments').strip() or 'payments'
        color = data.get('color_hex', '#163300').strip() or '#163300'

        account = Account.objects.create(
            user=profile,
            name=name,
            account_type=account_type,
            institution_name=name,
            icon=icon,
            color_hex=color,
            is_active=True
        )

        return JsonResponse({
            'success': True,
            'account': {
                'id': str(account.id),
                'name': account.name,
                'account_type': account.account_type,
                'account_type_display': account.get_account_type_display(),
                'icon': account.icon,
                'color_hex': account.color_hex,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['POST', 'PUT'])
def api_update_account(request, pk):
    """
    Update or Rename an Account / Payment Method.
    """
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    account = get_object_or_404(Account, id=pk, user=profile)

    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        if name:
            account.name = name
            account.institution_name = name

        if 'account_type' in data and data['account_type'] in dict(Account.AccountType.choices):
            account.account_type = data['account_type']

        if 'icon' in data and data['icon'].strip():
            account.icon = data['icon'].strip()

        if 'color_hex' in data and data['color_hex'].strip():
            account.color_hex = data['color_hex'].strip()

        account.save()

        return JsonResponse({
            'success': True,
            'account': {
                'id': str(account.id),
                'name': account.name,
                'account_type': account.account_type,
                'account_type_display': account.get_account_type_display(),
                'icon': account.icon,
                'color_hex': account.color_hex,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['POST', 'DELETE'])
def api_delete_account(request, pk):
    """
    Delete or Deactivate an Account / Payment Method.
    """
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    active_count = Account.objects.filter(user=profile, is_active=True).count()
    if active_count <= 1:
        return JsonResponse({'error': 'You must keep at least one active payment method.'}, status=400)

    account = get_object_or_404(Account, id=pk, user=profile)
    account.is_active = False
    account.save()

    return JsonResponse({'success': True, 'deleted_id': str(pk)})


@csrf_exempt
@require_GET
def api_list_categories(request):
    """
    List all categories for current user with their budget limit status.
    """
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    today = date.today()
    start_of_month = today.replace(day=1)

    categories = Category.objects.filter(user=profile).order_by('name')
    cats_data = []
    for cat in categories:
        budget = Budget.objects.filter(user=profile, category=cat, is_active=True).first()
        cats_data.append({
            'id': str(cat.id),
            'name': cat.name,
            'category_type': cat.category_type,
            'category_type_display': cat.get_category_type_display(),
            'icon_name': cat.icon_name,
            'color_hex': cat.color_hex,
            'has_budget': bool(budget and budget.amount_limit > 0),
            'amount_limit': float(budget.amount_limit) if budget else None,
            'limit_formatted': f"₱{budget.amount_limit:,.2f}" if budget and budget.amount_limit > 0 else "No Limit (Track only)",
        })

    return JsonResponse({'categories': cats_data})


@csrf_exempt
@require_POST
def api_create_category(request):
    """
    Create a new Category with optional Budget limit (support for inevitable / unbudgeted tracking).
    """
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        name = (data.get('name') or '').strip()
        if not name:
            return JsonResponse({'error': 'Category name is required.'}, status=400)

        category_type = data.get('category_type') or Category.CategoryType.EXPENSE
        icon_name = data.get('icon_name') or data.get('icon') or 'category'
        color_hex = data.get('color_hex') or data.get('color') or '#5C8F3A'
        has_budget = bool(data.get('has_budget', False))
        raw_limit = data.get('amount_limit') or data.get('amount')

        category = Category.objects.create(
            user=profile,
            name=name,
            category_type=category_type,
            icon_name=icon_name,
            color_hex=color_hex
        )

        budget_id = None
        if has_budget and raw_limit:
            try:
                limit_val = Decimal(str(raw_limit))
                if limit_val > 0:
                    today = date.today()
                    start_of_month = today.replace(day=1)
                    if today.month == 12:
                        end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
                    else:
                        end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

                    budget = Budget.objects.create(
                        user=profile,
                        category=category,
                        name=f"{category.name} Budget",
                        period_type=Budget.PeriodType.MONTHLY,
                        amount_limit=limit_val,
                        start_date=start_of_month,
                        end_date=end_of_month,
                        is_active=True
                    )
                    budget_id = str(budget.id)
            except Exception:
                pass

        return JsonResponse({
            'success': True,
            'category': {
                'id': str(category.id),
                'name': category.name,
                'category_type': category.category_type,
                'icon_name': category.icon_name,
                'color_hex': category.color_hex,
                'has_budget': has_budget and bool(budget_id),
                'amount_limit': float(raw_limit) if (has_budget and raw_limit) else None,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def api_update_category(request, pk):
    """
    Update category name, icon, color, and optional budget limit.
    """
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        category = get_object_or_404(Category, id=pk, user=profile)

        if 'name' in data and data['name'].strip():
            category.name = data['name'].strip()
        if 'icon_name' in data and data['icon_name']:
            category.icon_name = data['icon_name']
        if 'color_hex' in data and data['color_hex']:
            category.color_hex = data['color_hex']
        if 'category_type' in data and data['category_type']:
            category.category_type = data['category_type']

        category.save()

        # Handle optional budget limit toggle
        if 'has_budget' in data:
            has_budget = bool(data['has_budget'])
            raw_limit = data.get('amount_limit') or data.get('amount')

            if not has_budget or not raw_limit or Decimal(str(raw_limit)) <= 0:
                # Remove budget constraint (Inevitable / Tracking Only)
                Budget.objects.filter(user=profile, category=category).delete()
            else:
                limit_val = Decimal(str(raw_limit))
                today = date.today()
                start_of_month = today.replace(day=1)
                if today.month == 12:
                    end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

                Budget.objects.update_or_create(
                    user=profile,
                    category=category,
                    period_type=Budget.PeriodType.MONTHLY,
                    defaults={
                        'name': f"{category.name} Budget",
                        'amount_limit': limit_val,
                        'start_date': start_of_month,
                        'end_date': end_of_month,
                        'is_active': True
                    }
                )

        return JsonResponse({
            'success': True,
            'category': {
                'id': str(category.id),
                'name': category.name,
                'icon_name': category.icon_name,
                'color_hex': category.color_hex,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['POST', 'DELETE'])
def api_delete_category(request, pk):
    """
    Delete a Category and its associated Budget.
    """
    profile = get_current_user_profile(request)
    if not profile:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    category = get_object_or_404(Category, id=pk, user=profile)
    # Delete associated budgets
    Budget.objects.filter(user=profile, category=category).delete()
    category.delete()

    return JsonResponse({'success': True, 'deleted_id': str(pk)})


from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('budget/', views.budget_view, name='budget'),
    path('reports/', views.reports_view, name='reports'),
    path('receipt-detail/', views.receipt_detail_view, name='receipt_detail'),
    path('receipt-detail/<uuid:pk>/', views.receipt_detail_view, name='receipt_detail_pk'),
    path('add/', views.add_transaction_view, name='add_transaction'),
    path('scan-receipt/', views.scan_receipt_view, name='scan_receipt'),
    path('scan/', views.scan_receipt_view, name='scan_alias'),
    
    # JSON API Endpoints
    path('api/scan-receipt/', views.api_scan_receipt_view, name='api_scan_receipt'),
    path('api/transactions/create/', views.api_create_transaction, name='api_create_transaction'),
    path('api/transactions/<uuid:pk>/update/', views.api_update_transaction, name='api_update_transaction'),
    path('api/transactions/<uuid:pk>/delete/', views.api_delete_transaction, name='api_delete_transaction'),
    path('api/budgets/save/', views.api_save_budget, name='api_save_budget'),
    path('api/receipts/<uuid:pk>/update-items/', views.api_update_receipt_items, name='api_update_receipt_items'),
    path('api/receipts/<uuid:pk>/delete/', views.api_delete_receipt, name='api_delete_receipt'),
    
    # Account & Payment Method APIs
    path('api/accounts/', views.api_list_accounts, name='api_list_accounts'),
    path('api/accounts/create/', views.api_create_account, name='api_create_account'),
    path('api/accounts/<uuid:pk>/update/', views.api_update_account, name='api_update_account'),
    path('api/accounts/<uuid:pk>/delete/', views.api_delete_account, name='api_delete_account'),

    # Category Management APIs
    path('api/categories/', views.api_list_categories, name='api_list_categories'),
    path('api/categories/create/', views.api_create_category, name='api_create_category'),
    path('api/categories/<uuid:pk>/update/', views.api_update_category, name='api_update_category'),
    path('api/categories/<uuid:pk>/delete/', views.api_delete_category, name='api_delete_category'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('budget/', views.budget_view, name='budget'),
    path('reports/', views.reports_view, name='reports'),
    path('receipt-detail/', views.receipt_detail_view, name='receipt_detail'),
    path('add/', views.add_transaction_view, name='add_transaction'),
    path('scan-receipt/', views.scan_receipt_view, name='scan_receipt'),
    path('api/scan-receipt/', views.api_scan_receipt_view, name='api_scan_receipt'),
]


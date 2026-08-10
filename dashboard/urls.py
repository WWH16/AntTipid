from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('transactions/', views.transactions_view, name='transactions'),
]

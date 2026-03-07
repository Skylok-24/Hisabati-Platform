from django.urls import path, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

schema_view = get_schema_view(
   openapi.Info(
      title="Announcements API",
      default_version='v1',
      description="API documentation for announcements project",
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

urlpatterns = [

    # Auth APIs
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('google_login/', views.google_login, name='google_login'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('change-password/', views.change_password, name='change_password'),
    path('reset-password-request/', views.reset_password_request, name='reset_password_request'),
    path('reset-password-confirm/', views.reset_password_confirm, name='reset_password_confirm'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register_page/', views.CountryListView.as_view(), name='country-list'),

    # Public announcements
    path('', views.CountryAnnouncementsView.as_view()),
    path('announcements/search/', views.AnnouncementSearchView.as_view(), name='announcement-search'),
    path('announcements/filter/', views.AnnouncementFilterView.as_view(), name='announcement-filter'),
    path('supported-countries/', views.CountryRateListView.as_view(), name='supported-countries-list'),
    path("announcements/<int:id>/", views.AnnouncementDetailView.as_view(), name='announcement-detail'),

    # Seller APIs
    path("seller/announcements/", views.SellerAnnouncementsListView.as_view(), name='seller-announcements-list'),
    path("seller/announcements/<int:id>/", views.SellerAnnouncementManageView.as_view(), name='seller-announcement-detail'),

    # Swagger documentation
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
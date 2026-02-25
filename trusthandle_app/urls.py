from django.urls import path
from . import views

urlpatterns = [
    path('',views.CountryAnnouncementsView.as_view()),
    path('login/',views.login_view,name='login'),
    path('register/',views.register,name='register'),
    path('google_login/',views.google_login,name='google_login'),
    path('verify_otp/',views.verify_otp,name='verify_otp'),
    path("announcements/latest/", views.LatestAnnouncementsView.as_view()),
]
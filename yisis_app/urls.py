from django.urls import path
from .views import *
urlpatterns = [
    path("",home,name="home"),
    path("infos/",Infos.as_view(),name="infos"),
    path("stations/",Stations.as_view(),name="stations"),
    path("user-info/", UserInfoView.as_view(), name="user-info"),
    path("fire-report/",CreateFireReportView.as_view(),name="fire_report"),
    path("fire-report-all/",ListAllFireReportsView.as_view(),name="fire_report-all"),
    path("fire-report-user/",ListUserFireReportsView.as_view(),name="fire_report-user"),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('update-push-token/',UpdatePushTokenView.as_view(), name='update_push_token'),

]

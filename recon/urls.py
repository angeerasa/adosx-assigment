from django.urls import path

from recon import views

urlpatterns = [
    path("exceptions/", views.DiscrepancyView.as_view(), name="exceptions-list"),
    path("ask/", views.AskQuestionView.as_view(), name="ask"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
]
from django.contrib.auth import logout, authenticate, login
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from recon.models import Discrepancy
from recon.serializers import DiscrepancySerializer


# Create your views here.
class DiscrepancyView(generics.ListAPIView):
    serializer_class = DiscrepancySerializer

    def get_queryset(self):
        qs = Discrepancy.objects.all()

        reason_code = self.request.query_params.get("reason_code")
        location_id = self.request.query_params.get("location_id")

        qs.filter(reason_code=reason_code, location_id=location_id)

        return qs
#Angeerasa: will implement using OpenAI
# class AskQuestionView(APIView):
#     def post(self,request):
#         q = request.data.get("question","")
#         ord_id = request.user.org_membership.org_id
#
#         result = answer_question(question, ord_id)
#
#         return Response(result)
#
@method_decorator(csrf_exempt, name="dispatch")
class LoginView(View):
    def post(self, request):
        import json
        body = json.loads(request.body or "{}")
        user = authenticate(request, username=body.get("username"), password=body.get("password"))
        if user is None:
            return JsonResponse({"error": "invalid credentials"}, status=401)
        login(request, user)
        org_id = user.org_membership.org_id if hasattr(user, "org_membership") else None
        return JsonResponse({"username": user.username, "org_id": org_id})


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(View):
    def post(self, request):
        logout(request)
        return JsonResponse({"ok": True})


class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"authenticated": False})
        membership = getattr(request.user, "org_membership", None)
        return Response({
            "authenticated": True,
            "username": request.user.username,
            "org_id": membership.org_id if membership else None,
        })
import json

from django.contrib.auth import logout, authenticate, login
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from recon.answer import answer_question
from recon.models import Discrepancy
from recon.serializers import DiscrepancySerializer


# Create your views here.
class DiscrepancyView(generics.ListAPIView):
    serializer_class = DiscrepancySerializer

    def get_queryset(self):
        qs = Discrepancy.objects.all()

        reason_code = self.request.query_params.get("reason_code")
        location_id = self.request.query_params.get("location_id")
        # print("Angeerasa", reason_code)
        qs.filter(reason_code=reason_code, location_id=location_id)#Angeerasa Claude gave this line
        if reason_code:
            qs = qs.filter(reason_code=reason_code)
        if location_id:
            qs = qs.filter(location_id=location_id)

        return qs
#Angeerasa: will implement using OpenAI
@method_decorator(csrf_exempt, name="dispatch")
class AskQuestionView(View):
    def post(self,request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "authentication required"}, status=401)

        body = json.loads(request.body or "{}")
        question = body.get("question", "")
        org_id = request.user.org_membership.org_id
        result = answer_question(question, org_id)
        return JsonResponse(result)

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
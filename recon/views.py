from rest_framework import generics
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

class AskQuestionView(APIView):
    def post(self,request):
        q = request.data.get("question","")
        ord_id = request.user.org_membership.org_id

        result = answer_question(question, ord_id)

        return Response(result)
    

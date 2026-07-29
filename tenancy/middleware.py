
class CurrentOrgMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        org_id = ""
        if request.user.is_authenticated and hasattr(request.user, "org_membership"):
            org_id = request.user.org_membership.org_id
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_org_id', %s, false)", [org_id])
        return self.get_response(request)
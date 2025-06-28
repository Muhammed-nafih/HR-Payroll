from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...api_decorators.base.decorators import manager_permission_required


class AttendancePermissionCheck(APIView):
    permission_classes = [IsAuthenticated]

    @manager_permission_required("attendance.view_attendance")
    def get(self, request):
        return Response(status=200)


class AttendancePermissionCheck(APIView):
    permission_classes = [IsAuthenticated]

    @manager_permission_required("attendance.view_attendance")
    def get(self, request):

        return Response(status=200)
    

class AttendancePermissionCheck(APIView):
    permission_classes = [IsAuthenticated]

    @manager_permission_required("attendance.view_attendance")
    def get(self, request):
        """
        This API checks if the user has permission to view attendance.
        """
        return Response(status=200)    

from rest_framework.permissions import BasePermission

class ManagerCanEnter(BasePermission):
    """
    Custom permission to check if the user has access to specific attendance actions.
    """

    def has_permission(self, request, view):
        return request.user.has_perm("attendance.change_attendance")  # Adjust permission name

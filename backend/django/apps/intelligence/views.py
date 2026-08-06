"""Intelligence app endpoints."""

from typing import Any

from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle


@extend_schema(
    summary='Intelligence service liveness probe',
    description='Returns 200 if the intelligence app is reachable.',
    responses=OpenApiTypes.OBJECT,
)
@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def health_view(_request: Any) -> Response:
    """Liveness probe for the intelligence app."""
    return Response(
        {'status': 'ok', 'service': 'intelligence'},
        status=status.HTTP_200_OK,
    )

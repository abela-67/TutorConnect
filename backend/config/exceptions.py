import logging

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """Consistent JSON errors; unexpected errors are logged but never leak internals to the client."""
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(exc.messages)
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = exception_handler(exc, context)
    if response is not None:
        return response

    logger.exception("Unhandled API error", exc_info=exc)
    return Response({"detail": "An unexpected error occurred. Please try again later."}, status=500)

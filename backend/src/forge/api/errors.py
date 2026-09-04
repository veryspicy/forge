"""Unified API error contract.

Spec: docs/ERROR-CODE-CONVENTION.md
Design notes (aligned with RFC 9457 / Stripe / Google AIP-193):
- backend emits stable machine codes only; human-facing text is produced by
  clients via locale mapping on ``errors.<code>``.
- every error code is registered here (single source of truth) with its
  error type / http status / developer-facing english message.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error taxonomy
# ---------------------------------------------------------------------------


class ErrorType(StrEnum):
    """Coarse category consumed by client UI branches (toast, retry, focus)."""

    AUTH_ERROR = "AUTH_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RESOURCE_ERROR = "RESOURCE_ERROR"
    CONFLICT_ERROR = "CONFLICT_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    SERVER_ERROR = "SERVER_ERROR"


class ErrorCode(StrEnum):
    """Stable machine codes — the only codes allowed in error responses.

    Naming: UPPER_SNAKE_CASE, self-describing. New business codes should be
    domain-prefixed (e.g. ORDER_*, CATALOG_*, PAYMENT_*); auth codes keep
    their legacy unprefixed form for backward compatibility.
    """

    # Auth / authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    FORBIDDEN = "FORBIDDEN"
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    REQUIRED_FIELD = "REQUIRED_FIELD"

    # Resource
    NOT_FOUND = "NOT_FOUND"

    # Customers (C-end users) management
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"
    CUSTOMER_CANNOT_DELETE = "CUSTOMER_CANNOT_DELETE"

    # Conflict
    CONFLICT = "CONFLICT"
    EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"

    # Admin RBAC / roles
    ROLE_NAME_EXISTS = "ROLE_NAME_EXISTS"
    INVALID_PERMISSION_IDS = "INVALID_PERMISSION_IDS"
    ROLE_NOT_FOUND = "ROLE_NOT_FOUND"
    SUPER_ADMIN_ROLE_FIXED = "SUPER_ADMIN_ROLE_FIXED"
    SYSTEM_ROLE_PROTECTED = "SYSTEM_ROLE_PROTECTED"

    # Admin MCP API keys
    MCP_KEY_NAME_REQUIRED = "MCP_KEY_NAME_REQUIRED"
    MCP_KEY_INVALID_SCOPE = "MCP_KEY_INVALID_SCOPE"
    MCP_KEY_SCOPES_REQUIRED = "MCP_KEY_SCOPES_REQUIRED"
    MCP_KEY_NOT_FOUND = "MCP_KEY_NOT_FOUND"

    # Common validation
    INVALID_ID = "INVALID_ID"

    # Rate limit / server
    RATE_LIMITED = "RATE_LIMITED"
    SERVER_ERROR = "SERVER_ERROR"


@dataclass(frozen=True)
class ErrorSpec:
    type_: ErrorType
    http_status: int
    message: str


@dataclass
class FieldError:
    """Field-level error detail (validation / targeted conflicts)."""

    field: str
    code: str
    message: str = ""


# ---------------------------------------------------------------------------
# Registry (single source of truth)
# ---------------------------------------------------------------------------


_REGISTRY: dict[ErrorCode, ErrorSpec] = {
    # Auth / authorization
    ErrorCode.UNAUTHORIZED: ErrorSpec(ErrorType.AUTH_ERROR, 401, "Authentication required."),
    ErrorCode.TOKEN_EXPIRED: ErrorSpec(ErrorType.AUTH_ERROR, 401, "Token has expired."),
    ErrorCode.INVALID_CREDENTIALS: ErrorSpec(ErrorType.AUTH_ERROR, 401, "Invalid email or password."),
    ErrorCode.ACCOUNT_DISABLED: ErrorSpec(ErrorType.AUTH_ERROR, 403, "Account is disabled."),
    ErrorCode.FORBIDDEN: ErrorSpec(ErrorType.AUTH_ERROR, 403, "Insufficient permissions."),
    ErrorCode.USER_NOT_FOUND: ErrorSpec(ErrorType.RESOURCE_ERROR, 404, "User does not exist."),
    # Validation
    ErrorCode.VALIDATION_ERROR: ErrorSpec(ErrorType.VALIDATION_ERROR, 422, "Request validation failed."),
    ErrorCode.BAD_REQUEST: ErrorSpec(ErrorType.VALIDATION_ERROR, 400, "Bad request."),
    ErrorCode.REQUIRED_FIELD: ErrorSpec(ErrorType.VALIDATION_ERROR, 422, "A required field is missing."),
    # Resource
    ErrorCode.NOT_FOUND: ErrorSpec(ErrorType.RESOURCE_ERROR, 404, "Resource not found."),
    # Customers (C-end users) management
    ErrorCode.CUSTOMER_NOT_FOUND: ErrorSpec(ErrorType.RESOURCE_ERROR, 404, "Customer does not exist."),
    ErrorCode.CUSTOMER_CANNOT_DELETE: ErrorSpec(
        ErrorType.CONFLICT_ERROR, 409, "Customer has orders or pet profiles and cannot be deleted; freeze instead."
    ),
    # Conflict
    ErrorCode.CONFLICT: ErrorSpec(ErrorType.CONFLICT_ERROR, 409, "Resource state conflict."),
    ErrorCode.EMAIL_ALREADY_REGISTERED: ErrorSpec(ErrorType.CONFLICT_ERROR, 409, "Email already registered."),
    # Admin RBAC / roles
    ErrorCode.ROLE_NAME_EXISTS: ErrorSpec(ErrorType.CONFLICT_ERROR, 400, "A role with this name already exists."),
    ErrorCode.INVALID_PERMISSION_IDS: ErrorSpec(ErrorType.VALIDATION_ERROR, 400, "Some permission ids are invalid."),
    ErrorCode.ROLE_NOT_FOUND: ErrorSpec(ErrorType.RESOURCE_ERROR, 404, "Role does not exist."),
    ErrorCode.SUPER_ADMIN_ROLE_FIXED: ErrorSpec(
        ErrorType.CONFLICT_ERROR, 400, "The super admin role is fixed and cannot be modified."
    ),
    ErrorCode.SYSTEM_ROLE_PROTECTED: ErrorSpec(
        ErrorType.CONFLICT_ERROR, 400, "System roles are protected and cannot be deleted."
    ),
    # Admin MCP API keys
    ErrorCode.MCP_KEY_NAME_REQUIRED: ErrorSpec(ErrorType.VALIDATION_ERROR, 400, "API key name is required."),
    ErrorCode.MCP_KEY_INVALID_SCOPE: ErrorSpec(ErrorType.VALIDATION_ERROR, 400, "Requested scope is not supported."),
    ErrorCode.MCP_KEY_SCOPES_REQUIRED: ErrorSpec(
        ErrorType.VALIDATION_ERROR, 400, "At least one of read/write scopes is required."
    ),
    ErrorCode.MCP_KEY_NOT_FOUND: ErrorSpec(ErrorType.RESOURCE_ERROR, 404, "API key not found."),
    # Common validation
    ErrorCode.INVALID_ID: ErrorSpec(ErrorType.VALIDATION_ERROR, 400, "Identifier is not a valid UUID."),
    # Rate limit / server
    ErrorCode.RATE_LIMITED: ErrorSpec(ErrorType.RATE_LIMIT_ERROR, 429, "Too many requests, slow down."),
    ErrorCode.SERVER_ERROR: ErrorSpec(ErrorType.SERVER_ERROR, 500, "Internal server error."),
}

# HTTP status -> fallback code for legacy/unknown HTTPException details.
_STATUS_FALLBACK: dict[int, ErrorCode] = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
}


def spec_for(code: ErrorCode | str) -> ErrorSpec:
    """Resolve registry spec for a code; unknown codes fall back to server error."""
    try:
        return _REGISTRY[ErrorCode(code)]
    except (KeyError, ValueError):
        logger.warning("Unregistered error code used: %s", code)
        return _REGISTRY[ErrorCode.SERVER_ERROR]


def fallback_for_status(status_code: int) -> ErrorCode:
    return _STATUS_FALLBACK.get(status_code, ErrorCode.SERVER_ERROR)


def registered_codes() -> list[str]:
    """Expose registered codes for cross-repo consistency checks."""
    return [code.value for code in _REGISTRY]


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class APIError(Exception):
    """Raise in endpoints/services to emit a registered error code.

    Usage:
        raise APIError(code=ErrorCode.EMAIL_ALREADY_REGISTERED)
        raise APIError(code=ErrorCode.EMAIL_ALREADY_REGISTERED, errors=[...])
    """

    def __init__(
        self,
        code: ErrorCode | str,
        *,
        message: str | None = None,
        errors: list[FieldError] | None = None,
        http_status: int | None = None,
    ) -> None:
        """Raise an API error.

        ``http_status`` overrides the registry default for edge cases where the
        same code must carry a different status (e.g. auth endpoints reporting
        a vanished account as 401 to trigger client re-login).
        """
        try:
            parsed = ErrorCode(code)
        except (KeyError, ValueError):
            logger.warning("Unregistered error code used: %s", code)
            parsed = ErrorCode.SERVER_ERROR
        spec = spec_for(parsed)
        self.code = parsed
        self.type_ = spec.type_
        self.http_status = http_status or spec.http_status
        self.message = message or spec.message
        self.errors = errors or []
        super().__init__(self.code.value)


# ---------------------------------------------------------------------------
# Response payload helpers
# ---------------------------------------------------------------------------


def _payload(
    code: ErrorCode,
    message: str,
    errors: list[FieldError] | None = None,
    status_code: int | None = None,
) -> dict[str, Any]:
    spec = spec_for(code)
    payload: dict[str, Any] = {
        "code": code.value,
        "message": message,
        "status": spec.http_status if status_code is None else status_code,
    }
    if errors:
        payload["errors"] = [
            {
                "field": err.field,
                "code": err.code,
                **({"message": err.message} if err.message else {}),
            }
            for err in errors
        ]
    return payload


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def _api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    api_error = cast(APIError, exc)
    return JSONResponse(
        status_code=api_error.http_status,
        content=_payload(
            ErrorCode(api_error.code),
            api_error.message,
            api_error.errors,
            status_code=api_error.http_status,
        ),
    )


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Normalize legacy HTTPException usages.

    - registered code in ``detail`` -> keep the code (migration path)
    - anything else (chinese / free text) -> status-based fallback code,
      original detail is NEVER echoed to the client.
    """
    http_exc = cast(HTTPException, exc)
    detail = http_exc.detail
    if isinstance(detail, str):
        try:
            code = ErrorCode(detail)
            if code in _REGISTRY:
                spec = spec_for(code)
                return JSONResponse(
                    status_code=http_exc.status_code,
                    content=_payload(code, spec.message),
                )
        except ValueError:
            pass
    fallback = fallback_for_status(http_exc.status_code)
    spec = spec_for(fallback)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=_payload(fallback, spec.message),
    )


async def _validation_handler(request: Request, exc: Exception) -> JSONResponse:
    validation_exc = cast(RequestValidationError, exc)
    field_errors: list[FieldError] = []
    for err in validation_exc.errors():
        loc = err.get("loc") or ()
        field = ".".join(str(part) for part in loc[1:]) if len(loc) > 1 else ".".join(str(part) for part in loc)
        code = "REQUIRED_FIELD" if err.get("type") == "missing" else "VALIDATION_ERROR"
        field_errors.append(FieldError(field=field or "body", code=code, message=str(err.get("msg", ""))))
    return JSONResponse(
        status_code=422,
        content=_payload(ErrorCode.VALIDATION_ERROR, "Request validation failed.", field_errors),
    )


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server error on %s %s", request.method, request.url.path)
    spec = spec_for(ErrorCode.SERVER_ERROR)
    return JSONResponse(
        status_code=500,
        content=_payload(ErrorCode.SERVER_ERROR, spec.message),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach unified error handlers to a FastAPI app."""
    app.add_exception_handler(APIError, _api_error_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(Exception, _unhandled_handler)

from fastapi import HTTPException, status


# ── Base ──────────────────────────────────────────────────────────────────────

class AppException(HTTPException):
    """Base for all domain exceptions. Maps to a specific HTTP status code."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=self.__class__.status_code,
            detail=detail or self.__class__.detail,
        )


# ── 400 Bad Request ───────────────────────────────────────────────────────────

class BadRequestError(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Bad request."


# ── 401 Unauthorized ─────────────────────────────────────────────────────────

class AuthenticationError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication failed."

    def __init__(self, detail: str | None = None):
        super().__init__(detail)
        # Required by OAuth2 spec
        self.headers = {"WWW-Authenticate": "Bearer"}


class InvalidCredentialsError(AuthenticationError):
    detail = "Incorrect username or password."


class InvalidTokenError(AuthenticationError):
    detail = "Invalid or expired token."


# ── 403 Forbidden ─────────────────────────────────────────────────────────────

class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."


# ── 404 Not Found ─────────────────────────────────────────────────────────────

class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class UserNotFoundError(NotFoundError):
    detail = "User not found."


# ── 409 Conflict ──────────────────────────────────────────────────────────────

class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists."


class UsernameTakenError(ConflictError):
    detail = "Username already taken."


class EmailTakenError(ConflictError):
    detail = "Email already registered."


# ── 422 Unprocessable ─────────────────────────────────────────────────────────

class ValidationError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error."

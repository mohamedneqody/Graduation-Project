from fastapi import HTTPException, status

class AppException(HTTPException):
    """Base exception for all custom application errors."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundError(AppException):
    def __init__(self, resource_name: str = "Resource", resource_id: str = None):
        detail = f"{resource_name} not found." if not resource_id else f"{resource_name} with identifier '{resource_id}' not found."
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class BadRequestError(AppException):
    def __init__(self, detail: str = "Bad Request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class ForbiddenError(AppException):
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class ConflictError(AppException):
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class BusinessRuleViolation(AppException):
    def __init__(self, detail: str = "Business rule violation"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

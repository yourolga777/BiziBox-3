class AppError(Exception):
    status_code: int = 500

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AppNotFoundError(AppError):
    status_code = 404


class AppConflictError(AppError):
    status_code = 409


class AppForbiddenError(AppError):
    status_code = 403

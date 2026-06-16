class TempMailError(Exception):
    detail = "Temporary mail service is unavailable"
    code = "TEMP_MAIL_UNAVAILABLE"
    status_code = 503

    def __init__(
        self,
        detail: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.detail = detail or self.detail
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        super().__init__(self.detail)


class BrowserUnavailableError(TempMailError):
    detail = "Browser session is unavailable"
    code = "BROWSER_UNAVAILABLE"
    status_code = 503


class ElementNotFoundError(TempMailError):
    detail = "Required page element was not found"
    code = "ELEMENT_NOT_FOUND"
    status_code = 502


class EmailNotFoundError(TempMailError):
    detail = "Email was not found"
    code = "EMAIL_NOT_FOUND"
    status_code = 404


class TempMailTimeoutError(TempMailError):
    detail = "Temporary mail service timed out"
    code = "TEMP_MAIL_TIMEOUT"
    status_code = 504

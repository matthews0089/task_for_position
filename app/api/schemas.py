from pydantic import BaseModel, ConfigDict


class CurrentEmailResponse(BaseModel):
    email: str


class InboxEmail(BaseModel):
    id: str
    sender: str
    subject: str
    time: str


class EmailContent(BaseModel):
    id: str
    sender: str
    subject: str
    timestamp: str
    body: str


class ErrorResponse(BaseModel):
    detail: str
    code: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Email was not found",
                "code": "EMAIL_NOT_FOUND",
            },
        }
    )

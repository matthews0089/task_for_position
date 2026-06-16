from fastapi import APIRouter, Depends

from app.api.dependencies import TempMailServiceProvider, get_temp_mail_service
from app.api.schemas import CurrentEmailResponse, EmailContent, ErrorResponse, InboxEmail

router = APIRouter()

ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
    504: {"model": ErrorResponse},
}


@router.get("/email", response_model=CurrentEmailResponse, responses=ERROR_RESPONSES)
async def get_current_email(
    service: TempMailServiceProvider = Depends(get_temp_mail_service),
) -> CurrentEmailResponse:
    return CurrentEmailResponse(email=await service.get_current_email())


@router.get("/inbox", response_model=list[InboxEmail], responses=ERROR_RESPONSES)
async def get_inbox(
    service: TempMailServiceProvider = Depends(get_temp_mail_service),
) -> list[InboxEmail]:
    return await service.get_inbox()


@router.get("/email/{email_id}", response_model=EmailContent, responses=ERROR_RESPONSES)
async def get_email_content(
    email_id: str,
    service: TempMailServiceProvider = Depends(get_temp_mail_service),
) -> EmailContent:
    return await service.get_email_content(email_id)


@router.post("/email/refresh", response_model=CurrentEmailResponse, responses=ERROR_RESPONSES)
async def refresh_email(
    service: TempMailServiceProvider = Depends(get_temp_mail_service),
) -> CurrentEmailResponse:
    return CurrentEmailResponse(email=await service.refresh_email())

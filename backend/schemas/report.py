from pydantic import BaseModel


class CaseReportResponse(BaseModel):
    account_id: str
    case_report_text: str

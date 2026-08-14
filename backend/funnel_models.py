from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


OFFER_SOURCES = {"recruitment", "reactivation", "fundraising_activation", "board_transformation"}


class FunnelLeadCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    email: EmailStr
    phone: str = Field(min_length=1)
    organization: str = Field(min_length=1)
    website: Optional[str] = ""
    city: str = ""
    state_region: str = ""
    country: str = ""
    answers: Dict[str, Any]


class FunnelLeadResponse(BaseModel):
    lead_id: str
    result_token: str
    offer_source: str
    owner_email_status: str


class CheckoutRequest(BaseModel):
    lead_id: str = Field(min_length=1)
    tier: str
    origin_url: str = Field(min_length=1)
    internal_test: bool = False

    @field_validator("tier")
    @classmethod
    def valid_tier(cls, value: str) -> str:
        if value not in {"97", "497"}:
            raise ValueError("Tier must be 97 or 497")
        return value


class LeadResultResponse(BaseModel):
    lead_id: str
    offer_source: str
    name: str
    organization: str
    answers: Dict[str, Any]
    result: Dict[str, Any]
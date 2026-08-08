from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator, model_validator


COUNTRIES = {"United States", "United Kingdom"}
STATUSES = {
    "New Applicant", "Active", "Under Review", "Contacted", "Presented to Nonprofit",
    "Interviewing", "Placed on Board", "Paused", "Withdrawn",
}


class BoardApplicantCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: EmailStr
    phone: str = Field(min_length=1)
    linkedin_url: Optional[HttpUrl] = None
    country: str
    city: str = Field(min_length=1)
    state_region: str = Field(min_length=1)
    postal_code: Optional[str] = ""
    job_title: str = Field(min_length=1)
    employer: Optional[str] = ""
    professional_field: str = Field(min_length=1)
    years_experience: str = Field(min_length=1)
    skills: List[str] = Field(min_length=1)
    other_skill: Optional[str] = ""
    professional_summary: str = Field(min_length=1)
    causes: List[str] = Field(min_length=1)
    other_cause: Optional[str] = ""
    board_types: List[str] = Field(min_length=1)
    participation_preferences: List[str] = Field(min_length=1)
    geographic_preferences: str = Field(min_length=1)
    availability: str = Field(min_length=1)
    monthly_commitment: str = Field(min_length=1)
    previous_board_experience: str = Field(min_length=1)
    board_experience_details: Optional[str] = ""
    fundraising_activities: List[str] = Field(min_length=1)
    professional_relationships: str = Field(min_length=1)
    reason_for_joining: str = Field(min_length=1)
    commitment_answer: str = Field(min_length=1)
    understands_unpaid: str = Field(min_length=1)
    profile_sharing_permission: bool
    board_opportunity_consent: bool = True
    privacy_accepted: bool

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        if value not in COUNTRIES:
            raise ValueError("The Board Applicant Network is currently open only to professionals living in the United States and United Kingdom.")
        return value

    @field_validator("linkedin_url", mode="before")
    @classmethod
    def normalize_optional_linkedin(cls, value):
        return None if value in (None, "") else value

    @model_validator(mode="after")
    def validate_permissions(self):
        if not self.profile_sharing_permission or not self.privacy_accepted:
            raise ValueError("Required applicant permissions must be accepted.")
        if self.previous_board_experience.startswith("Yes") and not self.board_experience_details:
            raise ValueError("Board experience details are required for current or previous board members.")
        if "Something else" in self.skills and not self.other_skill:
            raise ValueError("Please describe your other skill.")
        if "Other" in self.causes and not self.other_cause:
            raise ValueError("Please describe your other cause.")
        return self


class ApplicantResponse(BaseModel):
    applicant_id: str
    first_name: str
    last_name: str
    email: EmailStr
    country: str
    created: bool
    resend_sync_status: str
    confirmation_email_status: str


class AdminLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class ApplicantAdminUpdate(BaseModel):
    status: Optional[str] = None
    internal_notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in STATUSES:
            raise ValueError("Invalid applicant status")
        return value
from fastapi import APIRouter

from app.schemas.common import SingleResponse
from app.schemas.enums import (
    ACADEMIC_POSITIONS,
    STAFF_ROLES,
    TECHNICAL_SPECIALIZATIONS,
    YEARS_OF_STUDY,
    humanize,
)
from app.schemas.meta import Option, RegistrationOptions, YearOption

router = APIRouter()


@router.get("/registration-options", response_model=SingleResponse[RegistrationOptions])
def registration_options():
    return SingleResponse[RegistrationOptions](
        data=RegistrationOptions(
            academic_positions=[
                Option(value=v, label=humanize(v)) for v in ACADEMIC_POSITIONS
            ],
            technical_specializations=[
                Option(value=v, label=humanize(v)) for v in TECHNICAL_SPECIALIZATIONS
            ],
            years_of_study=[
                YearOption(value=v, label=f"Year {v}") for v in YEARS_OF_STUDY
            ],
            roles=[Option(value="student", label="Student")]
            + [Option(value=v, label=humanize(v)) for v in STAFF_ROLES],
        )
    )

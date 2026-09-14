from pydantic import BaseModel


class Option(BaseModel):
    value: str
    label: str


class YearOption(BaseModel):
    value: int
    label: str


class RegistrationOptions(BaseModel):
    academic_positions: list[Option]
    technical_specializations: list[Option]
    years_of_study: list[YearOption]
    roles: list[Option]

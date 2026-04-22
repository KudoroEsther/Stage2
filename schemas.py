from pydantic import BaseModel, field_validator
from typing import Optional


class ProfileRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not isinstance(v, str):
            raise ValueError("name must be a string")
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip().lower()

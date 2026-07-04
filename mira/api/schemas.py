from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, field_validator, HttpUrl

from mira import mandate
from mira.types import Mandate

class RunRequest(BaseModel):
    case_id: str
    requester_role: Literal['victim', 'legal_rep', 'authorized_ngo']
    scope_urls: list[HttpUrl]
    legal_basis: str
    attestation: bool

    @field_validator('scope_urls')
    @classmethod
    def validate_scope_urls(cls, v: list[HttpUrl]) -> list[HttpUrl]:
        if not v:
            raise ValueError("scope_urls cannot be empty")
        for url in v:
            if url.host != "mock-host.local":
                raise ValueError("G-2/G-12: Only mock-host.local is allowed in demo mode")
        return v

    def to_mandate(self) -> Mandate:
        # Convert Pydantic HttpUrl to strings for the internal type
        urls_str = [str(url) for url in self.scope_urls]
        return mandate.capture_consent(
            case_id=self.case_id,
            requester_role=self.requester_role,
            scope_urls=urls_str,
            legal_basis=self.legal_basis,
            attestation=self.attestation
        )

class CaseCreated(BaseModel):
    case_id: str
    stream_url: str

class CaseStateResponse(BaseModel):
    case_id: str
    status: str

class MandateRequest(BaseModel):
    requester_role: Literal['victim', 'legal_rep', 'authorized_ngo']
    scope_urls: list[HttpUrl]
    legal_basis: str
    attestation: bool

    @field_validator('scope_urls')
    @classmethod
    def validate_scope_urls(cls, v: list[HttpUrl]) -> list[HttpUrl]:
        if not v:
            raise ValueError("scope_urls cannot be empty")
        for url in v:
            if url.host != "mock-host.local":
                raise ValueError("G-2/G-12: Only mock-host.local is allowed in demo mode")
        return v

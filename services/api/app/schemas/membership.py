from uuid import UUID

from pydantic import BaseModel


class CurrentMembership(BaseModel):
    profile_id: UUID
    email: str
    organization_id: UUID
    organization_slug: str
    role_id: UUID
    role_name: str
    department_id: UUID | None = None
    department_name: str | None = None

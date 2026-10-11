"""Verified request identity and organization context.

This value object is intentionally small. Domain modules should accept it at
authorization seams instead of accepting a caller-provided tenant string.
"""

from __future__ import annotations


from dataclasses import dataclass

from fastapi import HTTPException

from ...deps import AuthContext


@dataclass(frozen=True, slots=True)
class OrganizationContext:
    organization_id: str
    external_organization_id: str
    subject: str
    auth_mode: str
    roles: tuple[str, ...]
    jti: str = ""

    @classmethod
    def from_auth(cls, auth: AuthContext) -> "OrganizationContext":
        organization_id = auth.tenant_id.strip()
        if not organization_id:
            raise HTTPException(status_code=401, detail="Authenticated organization is required.")
        return cls(
            organization_id=organization_id,
            external_organization_id=(auth.external_organization_id or organization_id).strip(),
            subject=auth.subject.strip(),
            auth_mode=auth.auth_mode,
            roles=tuple(auth.roles),
            jti=auth.jti.strip(),
        )

    def allows_role(self, *required_roles: str) -> bool:
        if not required_roles:
            return True
        role_set = set(self.roles)
        return "super_admin" in role_set or bool(role_set.intersection(required_roles))

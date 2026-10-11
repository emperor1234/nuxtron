"""Search HTTP authorization annotation."""

from ...deps import AuthContext
from ...deps import require_auth
from fastapi import Depends
from typing import Annotated

AuthDep = Annotated[AuthContext, Depends(require_auth)]

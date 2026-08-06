"""FastAPI application entrypoint."""

import os

from . import legacy_main as _legacy_main
from .middleware.trusted_proxy import TrustedProxyMiddleware
from .routers.lindy_email_management import router as _lindy_email_router
from .routers.lindy_meeting_management import router as _lindy_meeting_router

app = _legacy_main.app
reset_rate_limits_for_tests = _legacy_main.reset_rate_limits_for_tests


def _ensure_router_registered(router) -> None:
    prefixes = [getattr(route, "path", "") for route in app.routes]
    candidate_paths = [getattr(route, "path", "") for route in router.routes]
    if candidate_paths and any(path in prefixes for path in candidate_paths):
        return
    app.include_router(router)


_ensure_router_registered(_lindy_email_router)
_ensure_router_registered(_lindy_meeting_router)

# Trusted-proxy header stripping (PDR §6.3 / WO-3).
#
# Registered last so it runs FIRST in the middleware stack (Starlette executes
# middleware in reverse add order). This guarantees spoofable headers like
# X-Client-Cert-Verified / X-Forwarded-Proto are stripped from untrusted peers
# before any auth or transport-security check consults them.
#
# Only enforce the trusted-proxy requirement when the corresponding security
# flags are on; otherwise the middleware is a no-op pass-through so local dev
# and tests are unaffected.
_require_mtls = os.environ.get("REQUIRE_MTLS", "false").strip().lower() == "true"
_enforce_https = os.environ.get("ENFORCE_HTTPS_HEADER", "false").strip().lower() == "true"
if _require_mtls or _enforce_https:
    app.add_middleware(
        TrustedProxyMiddleware,
        require_mtls=_require_mtls,
        enforce_https_header=_enforce_https,
    )


__all__ = ["app", "reset_rate_limits_for_tests"]

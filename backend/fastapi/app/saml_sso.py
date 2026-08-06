# pyright: reportMissingTypeArgument=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

import os
from urllib.parse import urlparse

from fastapi import Request

from .config import env_bool

SAML_BINDING_HTTP_POST = 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
SAML_BINDING_HTTP_REDIRECT = 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'


def is_saml_enabled() -> bool:
    return env_bool('SAML_ENABLED', False)


def _ensure_toolkit_available() -> None:
    try:
        import onelogin  # noqa: F401  # type: ignore[import-not-found]
    except Exception as ex:
        raise RuntimeError('SAML toolkit not installed. Install python3-saml to enable SSO.') from ex


def _base_url(request: Request) -> str:
    explicit = os.getenv('SAML_PUBLIC_BASE_URL', '').strip()
    if explicit:
        return explicit.rstrip('/')
    return str(request.base_url).rstrip('/')


def _settings(request: Request) -> dict[str, object]:
    base = _base_url(request)

    idp_entity_id = os.getenv('SAML_IDP_ENTITY_ID', '').strip()
    idp_sso_url = os.getenv('SAML_IDP_SSO_URL', '').strip()
    idp_slo_url = os.getenv('SAML_IDP_SLO_URL', '').strip()
    idp_x509 = os.getenv('SAML_IDP_X509_CERT', '').strip()

    if not idp_entity_id or not idp_sso_url:
        raise RuntimeError('SAML IdP settings are incomplete. Set SAML_IDP_ENTITY_ID and SAML_IDP_SSO_URL.')

    entity_id = os.getenv('SAML_SP_ENTITY_ID', '').strip() or f'{base}/auth/saml/metadata'
    acs_url = os.getenv('SAML_SP_ACS_URL', '').strip() or f'{base}/auth/saml/acs'
    sls_url = os.getenv('SAML_SP_SLS_URL', '').strip() or f'{base}/auth/saml/logout'

    # SP cert presence determines whether signing/encryption can be enabled
    sp_cert_present = bool(os.getenv('SAML_SP_X509_CERT', '').strip())
    sp_key_present = bool(os.getenv('SAML_SP_PRIVATE_KEY', '').strip())
    can_sign = sp_cert_present and sp_key_present

    # Signing: default ON when SP key material is configured
    sign_authn = env_bool('SAML_SIGN_AUTHN_REQUESTS', can_sign)
    sign_logout_req = env_bool('SAML_SIGN_LOGOUT_REQUESTS', can_sign)
    sign_logout_resp = env_bool('SAML_SIGN_LOGOUT_RESPONSES', can_sign)
    sign_metadata = env_bool('SAML_SIGN_METADATA', can_sign)

    # Assertion/NameID encryption: default ON when SP key material is configured.
    # Requires IdP support — can be overridden with SAML_ENCRYPT_ASSERTIONS=false.
    want_assertions_encrypted = env_bool('SAML_ENCRYPT_ASSERTIONS', can_sign)
    want_nameid_encrypted = env_bool('SAML_ENCRYPT_NAMEID', can_sign)
    nameid_encrypted = want_nameid_encrypted

    return {
        'strict': env_bool('SAML_STRICT', True),
        'debug': env_bool('SAML_DEBUG', False),
        'security': {
            'nameIdEncrypted': nameid_encrypted,
            'authnRequestsSigned': sign_authn,
            'logoutRequestSigned': sign_logout_req,
            'logoutResponseSigned': sign_logout_resp,
            'signMetadata': sign_metadata,
            'wantMessagesSigned': env_bool('SAML_WANT_MESSAGES_SIGNED', True),
            'wantAssertionsSigned': env_bool('SAML_WANT_ASSERTIONS_SIGNED', True),
            'wantAssertionsEncrypted': want_assertions_encrypted,
            'wantNameIdEncrypted': want_nameid_encrypted,
            'wantNameId': True,
            'requestedAuthnContext': True,
        },
        'sp': {
            'entityId': entity_id,
            'assertionConsumerService': {
                'url': acs_url,
                'binding': SAML_BINDING_HTTP_POST,
            },
            'singleLogoutService': {
                'url': sls_url,
                'binding': SAML_BINDING_HTTP_REDIRECT,
            },
            'x509cert': os.getenv('SAML_SP_X509_CERT', '').strip(),
            'privateKey': os.getenv('SAML_SP_PRIVATE_KEY', '').strip(),
        },
        'idp': {
            'entityId': idp_entity_id,
            'singleSignOnService': {
                'url': idp_sso_url,
                'binding': SAML_BINDING_HTTP_REDIRECT,
            },
            'singleLogoutService': {
                'url': idp_slo_url,
                'binding': SAML_BINDING_HTTP_REDIRECT,
            },
            'x509cert': idp_x509,
        },
    }


def _request_data(request: Request) -> dict[str, object]:
    host = request.headers.get('host', '')
    parsed = urlparse(str(request.url))
    scheme = parsed.scheme or 'http'
    port = str(parsed.port or (443 if scheme == 'https' else 80))

    return {
        'https': 'on' if scheme == 'https' else 'off',
        'http_host': host,
        'server_port': port,
        'script_name': parsed.path,
        'query_string': parsed.query,
        'get_data': dict(request.query_params),
        'post_data': {},
    }


def metadata_xml(request: Request) -> str:
    _ensure_toolkit_available()
    from onelogin.saml2.settings import OneLogin_Saml2_Settings  # type: ignore[import-not-found]

    settings = OneLogin_Saml2_Settings(_settings(request), sp_validation_only=False)
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    if errors:
        raise RuntimeError(f'Invalid SAML metadata: {", ".join(errors)}')
    return metadata.decode() if isinstance(metadata, bytes) else metadata


def login_url(request: Request, relay_state: str | None = None) -> str:
    _ensure_toolkit_available()
    from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-not-found]

    auth = OneLogin_Saml2_Auth(_request_data(request), old_settings=_settings(request))
    return auth.login(return_to=relay_state)


def process_acs(request: Request, saml_response: str) -> dict[str, object]:
    _ensure_toolkit_available()
    from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-not-found]

    req_data = _request_data(request)
    req_data['post_data'] = {'SAMLResponse': saml_response}
    auth = OneLogin_Saml2_Auth(req_data, old_settings=_settings(request))
    auth.process_response()
    errors = auth.get_errors()
    if errors:
        raise RuntimeError(f'SAML assertion validation failed: {", ".join(errors)}')
    if not auth.is_authenticated():
        raise RuntimeError('SAML authentication failed.')

    attributes = auth.get_attributes() or {}
    return {
        'name_id': auth.get_nameid(),
        'session_index': auth.get_session_index(),
        'name_id_format': auth.get_nameid_format(),
        'attributes': attributes,
    }

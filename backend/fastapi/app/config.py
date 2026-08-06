import os


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def required_security_vars_present() -> list[str]:
    required = [
        'FASTAPI_API_KEY',
        'PASSWORD_PEPPER',
        'APP_ENC_KEY',
    ]
    missing: list[str] = []
    for name in required:
        value = os.getenv(name, '').strip()
        if not value:
            missing.append(name)
    return missing


def validate_startup_security() -> None:
    environment = os.getenv('ENVIRONMENT', 'development').strip().lower()
    strict_mode = env_bool('SECURITY_STRICT_MODE', False) or environment == 'production'
    if not strict_mode:
        return

    missing = required_security_vars_present()
    if missing:
        joined = ', '.join(missing)
        raise RuntimeError(f'SECURITY_STRICT_MODE enabled but required vars are missing: {joined}')

    api_key = os.getenv('FASTAPI_API_KEY', '').strip()
    if api_key == 'change-this-fastapi-key':
        raise RuntimeError('FASTAPI_API_KEY must be changed from the default value in strict/production mode.')

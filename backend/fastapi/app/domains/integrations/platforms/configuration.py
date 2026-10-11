"""Platform deployment-mode policy independent of persistence adapters."""
import os

def _is_production_env() -> bool:
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'

"""Startup validation module for fail-closed initialization."""
import os
import sys
import json
from typing import Optional


class StartupValidationError(Exception):
    """Raised when a required configuration is absent or invalid."""

    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(f"Startup validation failed: {len(errors)} error(s)")


def validate_startup_config(
    settings: Optional[object] = None,
    env: Optional[dict] = None,
) -> None:
    """
    Validates all required environment variables.

    Raises StartupValidationError with a list of ALL errors found.
    Called BEFORE uvicorn starts accepting requests.

    Args:
        settings: Optional settings object with attributes for validation
        env: Optional dict of environment variables (defaults to os.environ)

    Returns:
        None if all validations pass

    Raises:
        StartupValidationError: If any required config is missing/invalid
    """
    if env is None:
        env = dict(os.environ)

    # If settings object provided, merge its attributes into env
    if settings is not None:
        for attr in dir(settings):
            if not attr.startswith("_") and hasattr(settings, attr):
                val = getattr(settings, attr)
                if isinstance(val, str):
                    env[attr] = val

    errors: list[dict] = []
    missing: list[str] = []
    empty: list[str] = []
    invalid: list[str] = []

    # REQUIRED: Must have value, fail-closed if missing
    required_vars = [
        "JWT_SECRET",
        "ADMIN_PASSWORD",
        "N8N_WEBHOOK_SECRET",
        "ENCRYPTION_MASTER_KEY",
        "DOMINUS_PRIVATE_KEY",
        "IDPW_PUBLIC_KEY",
        "IDENTITY_WORKER_URL",
        "WHATSAPP_API_URL",
        "WHATSAPP_PUBLIC_URL",
    ]

    for var in required_vars:
        value = env.get(var)
        if value is None:
            missing.append(var)
            errors.append({"variable": var, "type": "missing", "message": f"Environment variable {var} is not set"})
        elif value == "":
            empty.append(var)
            errors.append({"variable": var, "type": "empty", "message": f"Environment variable {var} is empty"})

    # REQUIRED_IN_PROD: DATABASE_URL required when ENVIRONMENT=production
    env_var = env.get("ENVIRONMENT", "development")
    db_url = env.get("DATABASE_URL", "")

    if env_var == "production" or env_var == "prod":
        if not db_url:
            missing.append("DATABASE_URL")
            errors.append({
                "variable": "DATABASE_URL",
                "type": "missing",
                "message": "DATABASE_URL is required in production (ENVIRONMENT=production)"
            })

    # Handle WEBHOOK_SECRET deprecation warning
    webhook_secret = env.get("WEBHOOK_SECRET", "")
    n8n_webhook_secret = env.get("N8N_WEBHOOK_SECRET", "")
    if webhook_secret and not n8n_webhook_secret:
        # Log warning but don't fail - this is a migration path
        print(f"WARNING: WEBHOOK_SECRET is deprecated. Use N8N_WEBHOOK_SECRET instead.", file=sys.stderr)

    # Validate ENCRYPTION_MASTER_KEY format (should be hex-encoded, 32 bytes = 64 hex chars)
    enc_key = env.get("ENCRYPTION_MASTER_KEY", "")
    if enc_key and len(enc_key) != 64:
        invalid.append("ENCRYPTION_MASTER_KEY")
        errors.append({
            "variable": "ENCRYPTION_MASTER_KEY",
            "type": "invalid",
            "message": "ENCRYPTION_MASTER_KEY must be 64 hex characters (32 bytes)"
        })

    if errors:
        output = {
            "error": "STARTUP_VALIDATION_FAILED",
            "missing": missing,
            "empty": empty,
            "invalid": invalid,
            "action": "Set the missing environment variables and restart."
        }
        print(json.dumps(output, indent=2), file=sys.stderr)
        raise StartupValidationError(errors)


def check_startup_config(settings: Optional[object] = None) -> bool:
    """
    Check if startup config is valid without raising exceptions.

    Args:
        settings: Optional settings object with attributes for validation

    Returns:
        True if all validations pass, False otherwise
    """
    try:
        validate_startup_config(settings)
        return True
    except StartupValidationError:
        return False

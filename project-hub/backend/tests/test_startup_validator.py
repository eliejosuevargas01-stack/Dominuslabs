"""
Tests for ARCH-002: Fail-closed startup validator.

Validates that:
- Startup fails when REQUIRED vars are missing
- Startup fails when REQUIRED vars are empty
- Startup passes when all REQUIRED vars are present
- DATABASE_URL is only required when ENVIRONMENT=production
- Multiple errors are collected simultaneously (not stopping at first)
- ENCRYPTION_MASTER_KEY format is validated (64 hex chars)
- WEBHOOK_SECRET deprecation warning is emitted
"""
import os
import json
import pytest
from unittest.mock import patch
from app.core.startup_validator import (
    validate_startup_config,
    check_startup_config,
    StartupValidationError,
)

# Minimal valid env that passes all validations
VALID_ENV = {
    "JWT_SECRET": "test-jwt-secret-key-32chars-minimum!!",
    "ADMIN_PASSWORD": "test-admin-password",
    "N8N_WEBHOOK_SECRET": "test-webhook-secret-32chars-min!",
    "ENCRYPTION_MASTER_KEY": "a" * 64,  # 64 hex chars
    "DOMINUS_PRIVATE_KEY": "test-private-key",
    "IDPW_PUBLIC_KEY": "test-public-key",
    "IDENTITY_WORKER_URL": "https://idpw.example.com",
    "WHATSAPP_API_URL": "http://localhost:3000",
    "WHATSAPP_PUBLIC_URL": "https://wa.example.com",
    "ENVIRONMENT": "development",
    "DATABASE_URL": "",  # Not required in development
}


class TestValidateStartupConfig:
    """Tests for validate_startup_config()."""

    def test_passes_with_all_required_vars(self):
        """Startup succeeds when all REQUIRED vars are present."""
        validate_startup_config(env=dict(VALID_ENV))  # Should not raise

    def test_fails_when_jwt_secret_missing(self):
        """Startup fails when JWT_SECRET is absent."""
        env = {k: v for k, v in VALID_ENV.items() if k != "JWT_SECRET"}
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("JWT_SECRET" in str(e) for e in exc_info.value.errors)

    def test_fails_when_jwt_secret_empty(self):
        """Startup fails when JWT_SECRET is empty string."""
        env = dict(VALID_ENV)
        env["JWT_SECRET"] = ""
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("JWT_SECRET" in str(e) for e in exc_info.value.errors)

    def test_fails_when_admin_password_missing(self):
        """Startup fails when ADMIN_PASSWORD is absent."""
        env = {k: v for k, v in VALID_ENV.items() if k != "ADMIN_PASSWORD"}
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("ADMIN_PASSWORD" in str(e) for e in exc_info.value.errors)

    def test_fails_when_encryption_master_key_missing(self):
        """Startup fails when ENCRYPTION_MASTER_KEY is absent."""
        env = {k: v for k, v in VALID_ENV.items() if k != "ENCRYPTION_MASTER_KEY"}
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("ENCRYPTION_MASTER_KEY" in str(e) for e in exc_info.value.errors)

    def test_fails_when_dominus_private_key_missing(self):
        """Startup fails when DOMINUS_PRIVATE_KEY is absent."""
        env = {k: v for k, v in VALID_ENV.items() if k != "DOMINUS_PRIVATE_KEY"}
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("DOMINUS_PRIVATE_KEY" in str(e) for e in exc_info.value.errors)

    def test_fails_when_idpw_public_key_missing(self):
        """Startup fails when IDPW_PUBLIC_KEY is absent."""
        env = {k: v for k, v in VALID_ENV.items() if k != "IDPW_PUBLIC_KEY"}
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("IDPW_PUBLIC_KEY" in str(e) for e in exc_info.value.errors)

    def test_fails_when_identity_worker_url_missing(self):
        """Startup fails when IDENTITY_WORKER_URL is absent."""
        env = {k: v for k, v in VALID_ENV.items() if k != "IDENTITY_WORKER_URL"}
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("IDENTITY_WORKER_URL" in str(e) for e in exc_info.value.errors)

    def test_fails_when_whatsapp_api_url_missing(self):
        """Startup fails when WHATSAPP_API_URL is absent."""
        env = {k: v for k, v in VALID_ENV.items() if k != "WHATSAPP_API_URL"}
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("WHATSAPP_API_URL" in str(e) for e in exc_info.value.errors)

    def test_fails_when_whatsapp_public_url_missing(self):
        """Startup fails when WHATSAPP_PUBLIC_URL is absent."""
        env = {k: v for k, v in VALID_ENV.items() if k != "WHATSAPP_PUBLIC_URL"}
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("WHATSAPP_PUBLIC_URL" in str(e) for e in exc_info.value.errors)

    def test_collects_multiple_errors_simultaneously(self):
        """All missing vars are reported, not just the first one."""
        env = {k: v for k, v in VALID_ENV.items() if k in ("ENVIRONMENT", "DATABASE_URL")}
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        # Should have errors for all 9 required vars
        assert len(exc_info.value.errors) >= 9

    def test_database_url_not_required_in_development(self):
        """DATABASE_URL is optional when ENVIRONMENT != production."""
        env = dict(VALID_ENV)
        env["ENVIRONMENT"] = "development"
        env["DATABASE_URL"] = ""
        validate_startup_config(env=env)  # Should not raise

    def test_database_url_required_in_production(self):
        """DATABASE_URL is required when ENVIRONMENT=production."""
        env = dict(VALID_ENV)
        env["ENVIRONMENT"] = "production"
        env["DATABASE_URL"] = ""
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("DATABASE_URL" in str(e) for e in exc_info.value.errors)

    def test_database_url_required_in_prod_alias(self):
        """DATABASE_URL is required when ENVIRONMENT=prod."""
        env = dict(VALID_ENV)
        env["ENVIRONMENT"] = "prod"
        env["DATABASE_URL"] = ""
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("DATABASE_URL" in str(e) for e in exc_info.value.errors)

    def test_encryption_master_key_must_be_64_hex_chars(self):
        """ENCRYPTION_MASTER_KEY must be exactly 64 characters."""
        env = dict(VALID_ENV)
        env["ENCRYPTION_MASTER_KEY"] = "tooshort"
        with pytest.raises(StartupValidationError) as exc_info:
            validate_startup_config(env=env)
        assert any("ENCRYPTION_MASTER_KEY" in str(e) for e in exc_info.value.errors)

    def test_webhook_secret_deprecation_warning(self, capsys):
        """WEBHOOK_SECRET without N8N_WEBHOOK_SECRET emits deprecation warning."""
        env = dict(VALID_ENV)
        env["WEBHOOK_SECRET"] = "old-secret"
        env["N8N_WEBHOOK_SECRET"] = ""
        with pytest.raises(StartupValidationError):
            validate_startup_config(env=env)
        captured = capsys.readouterr()
        assert "WEBHOOK_SECRET is deprecated" in captured.err


class TestCheckStartupConfig:
    """Tests for check_startup_config() — non-raising variant."""

    def test_returns_true_when_valid(self):
        """Returns True when all required vars are present."""
        with patch.dict(os.environ, VALID_ENV, clear=False):
            assert check_startup_config() is True

    def test_returns_false_when_invalid(self):
        """Returns False when required vars are missing."""
        minimal_env = {"ENVIRONMENT": "development", "DATABASE_URL": ""}
        with patch.dict(os.environ, minimal_env, clear=True):
            assert check_startup_config() is False


class TestErrorOutputFormat:
    """Tests for the JSON error output structure."""

    def test_error_output_is_json(self, capsys):
        """Error output is valid JSON with expected fields."""
        env = {k: v for k, v in VALID_ENV.items() if k != "JWT_SECRET"}
        with pytest.raises(StartupValidationError):
            validate_startup_config(env=env)
        captured = capsys.readouterr()
        # Find the JSON block in stderr
        lines = captured.err.strip().split("\n")
        json_start = next(i for i, l in enumerate(lines) if l.startswith("{"))
        json_text = "\n".join(lines[json_start:])
        parsed = json.loads(json_text)
        assert parsed["error"] == "STARTUP_VALIDATION_FAILED"
        assert "missing" in parsed
        assert "empty" in parsed
        assert "invalid" in parsed
        assert "action" in parsed

    def test_missing_vars_listed_in_output(self, capsys):
        """Missing variables appear in the 'missing' list."""
        env = {k: v for k, v in VALID_ENV.items() if k != "JWT_SECRET"}
        with pytest.raises(StartupValidationError):
            validate_startup_config(env=env)
        captured = capsys.readouterr()
        lines = captured.err.strip().split("\n")
        json_start = next(i for i, l in enumerate(lines) if l.startswith("{"))
        parsed = json.loads("\n".join(lines[json_start:]))
        assert "JWT_SECRET" in parsed["missing"]

    def test_empty_vars_listed_in_output(self, capsys):
        """Empty variables appear in the 'empty' list."""
        env = dict(VALID_ENV)
        env["JWT_SECRET"] = ""
        with pytest.raises(StartupValidationError):
            validate_startup_config(env=env)
        captured = capsys.readouterr()
        lines = captured.err.strip().split("\n")
        json_start = next(i for i, l in enumerate(lines) if l.startswith("{"))
        parsed = json.loads("\n".join(lines[json_start:]))
        assert "JWT_SECRET" in parsed["empty"]

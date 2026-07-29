"""Unit tests for MCP API Key authentication."""

from __future__ import annotations

import hashlib
from unittest.mock import patch

import pytest
import forge.infrastructure.mcp.auth as auth_mod


class TestMCPAuth:
    def test_validate_correct_api_key(self):
        secret = "my-secret-key"
        expected_hash = hashlib.sha256(secret.encode()).hexdigest()

        with patch.object(auth_mod, "_MCP_API_KEY_HASH", expected_hash):
            assert auth_mod.validate_api_key("my-secret-key") is True

    def test_validate_incorrect_api_key(self):
        secret = "my-secret-key"
        expected_hash = hashlib.sha256(secret.encode()).hexdigest()

        with patch.object(auth_mod, "_MCP_API_KEY_HASH", expected_hash):
            assert auth_mod.validate_api_key("wrong-key") is False

    def test_validate_empty_key_when_hash_not_set(self):
        """When _MCP_API_KEY_HASH is empty/not-set, any key passes (dev mode)."""
        with patch.object(auth_mod, "_MCP_API_KEY_HASH", ""):
            assert auth_mod.validate_api_key("any-key-works") is True

    def test_validate_key_not_set_default(self):
        """Explicit empty string also allows any key."""
        with patch.object(auth_mod, "_MCP_API_KEY_HASH", ""):
            assert auth_mod.validate_api_key("") is True

    def test_validate_hash_set_but_empty_key_provided(self):
        """Empty API key with hash set should fail."""
        secret = "my-secret-key"
        expected_hash = hashlib.sha256(secret.encode()).hexdigest()

        with patch.object(auth_mod, "_MCP_API_KEY_HASH", expected_hash):
            assert auth_mod.validate_api_key("") is False

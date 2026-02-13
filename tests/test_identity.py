import os
import shutil
import pytest
from identity import IdentityManager


@pytest.fixture
def identity_manager():
    test_dir = "data/test_keys"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    manager = IdentityManager(keys_dir=test_dir)
    yield manager
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


def test_create_identity(identity_manager):
    token = identity_manager.create_identity("test_user")
    assert token is not None
    assert len(token) == 64  # SHA-256 hex length
    assert "test_user" in identity_manager.list_identities()


def test_get_token(identity_manager):
    token1 = identity_manager.create_identity("user1")
    token2 = identity_manager.get_token("user1")
    assert token1 == token2


def test_sign_and_verify(identity_manager):
    identity_manager.create_identity("signer")
    pk = identity_manager.get_public_key("signer")
    message = b"hello world"
    signature = identity_manager.sign_message("signer", message)
    assert identity_manager.verify_signature(pk, message, signature) is True
    assert identity_manager.verify_signature(pk, b"wrong message", signature) is False

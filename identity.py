import hashlib
import os
from typing import Optional, List
from pqcrypto.sign.ml_dsa_44 import generate_keypair, sign, verify


class IdentityManager:
    def __init__(self, keys_dir: str = "data/keys") -> None:
        self.keys_dir = keys_dir
        os.makedirs(self.keys_dir, exist_ok=True)

    def create_identity(self, username: str) -> str:
        """Generates a new PQC (ML-DSA-44) key pair and saves the private key."""
        public_key, secret_key = generate_keypair()

        sk_path = os.path.join(self.keys_dir, f"{username}.sk")
        with open(sk_path, "wb") as f:
            f.write(secret_key)

        pk_path = os.path.join(self.keys_dir, f"{username}.pk")
        with open(pk_path, "wb") as f:
            f.write(public_key)

        token = hashlib.sha256(public_key).hexdigest()
        return token

    def get_token(self, username: str) -> Optional[str]:
        """Retrieves the token for an existing user by loading their PQC public key."""
        pk = self.get_public_key(username)
        if not pk:
            return None
        return hashlib.sha256(pk).hexdigest()

    def get_public_key(self, username: str) -> Optional[bytes]:
        """Retrieves the raw public key bytes for a user."""
        pk_path = os.path.join(self.keys_dir, f"{username}.pk")
        if not os.path.exists(pk_path):
            return None
        with open(pk_path, "rb") as f:
            return f.read()

    def list_identities(self) -> List[str]:
        """Lists all usernames that have PQC keys stored."""
        return [
            f.replace(".sk", "") for f in os.listdir(self.keys_dir) if f.endswith(".sk")
        ]

    def sign_message(self, username: str, message: bytes) -> bytes:
        """Signs a message using the user's PQC secret key."""
        sk_path = os.path.join(self.keys_dir, f"{username}.sk")
        with open(sk_path, "rb") as f:
            secret_key = f.read()
        return sign(secret_key, message)

    def verify_signature(
        self, public_key: bytes, message: bytes, signature: bytes
    ) -> bool:
        """Verifies a PQC signature."""
        try:
            return verify(public_key, message, signature) is None
        except Exception:
            return False

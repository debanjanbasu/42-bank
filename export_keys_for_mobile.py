"""Export backend keys for mobile app import."""
import base64
import json
import os

def uint8array_to_base64(arr):
    """Convert bytes to base64 string."""
    return base64.b64encode(arr).decode('utf-8')

def export_keys(username):
    """Export keys for a user."""
    keys_dir = os.path.join(os.path.dirname(__file__), 'data', 'keys')
    sk_path = os.path.join(keys_dir, f"{username}.sk")
    pk_path = os.path.join(keys_dir, f"{username}.pk")
    
    if not os.path.exists(sk_path):
        print(f"❌ Private key not found for {username}")
        return None
    
    with open(sk_path, 'rb') as f:
        private_key = f.read()
    
    with open(pk_path, 'rb') as f:
        public_key = f.read()
    
    private_key_b64 = uint8array_to_base64(private_key)
    public_key_b64 = uint8array_to_base64(public_key)
    
    result = {
        "username": username,
        "publicKey": public_key_b64,
        "privateKey": private_key_b64
    }
    
    print(f"✅ Keys exported for {username}")
    print(f"Public Key (first 50 chars): {public_key_b64[:50]}...")
    print(f"\nImport instructions:")
    print(f"1. Open the mobile app")
    print(f"2. Go to Settings")
    print(f"3. Tap 'Import Keys'")
    print(f"4. Paste this JSON:")
    print(json.dumps(result, indent=2))
    
    return result

if __name__ == "__main__":
    export_keys("alice")

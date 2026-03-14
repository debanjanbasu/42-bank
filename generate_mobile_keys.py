"""Generate mobile app import JSON for alice and bob."""
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
        print(f"❌ Keys not found for {username}")
        return None
    
    with open(sk_path, 'rb') as f:
        private_key = f.read()
    
    with open(pk_path, 'rb') as f:
        public_key = f.read()
    
    result = {
        "publicKey": uint8array_to_base64(public_key),
        "privateKey": uint8array_to_base64(private_key)
    }
    
    return json.dumps(result)

if __name__ == "__main__":
    print("=== MOBILE APP KEY IMPORT DATA ===\n")
    
    print("For ALICE - Copy this JSON:")
    print(export_keys("alice"))
    print("\n")
    
    print("For BOB - Copy this JSON:")
    print(export_keys("bob"))
    print("\n")
    
    print("=== INSTRUCTIONS ===")
    print("1. Open the mobile app")
    print("2. Go to Settings tab")
    print("3. Tap 'Import Keys'")
    print("4. Paste the JSON above")
    print("5. Tap 'Import'")
    print("\nNow you can send transactions!")

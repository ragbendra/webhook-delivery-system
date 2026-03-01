import hashlib
import hmac


def generate_hmac_sha256_signature(raw_payload: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw_payload.encode("utf-8"), hashlib.sha256).hexdigest()

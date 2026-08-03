import os
import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException

CLERK_JWKS_URL = os.environ.get(
    "CLERK_JWKS_URL", 
    "https://light-sawfly-76.clerk.accounts.dev/.well-known/jwks.json"
)

_jwk_client = PyJWKClient(CLERK_JWKS_URL) if CLERK_JWKS_URL else None


def get_current_user(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header.")

    token = authorization.split(" ", 1)[1]

    if not _jwk_client:
        raise HTTPException(status_code=500, detail="Auth is not configured on the server.")

    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(token, signing_key.key, algorithms=["RS256"], options={"verify_aud": False})
        return payload["sub"]  # Clerk's user ID
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
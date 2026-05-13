from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials


def build_admin_auth_dependency(user: str, password: str):
    basic = HTTPBasic()

    def require_admin(creds: HTTPBasicCredentials = Depends(basic)) -> str:
        ok_user = secrets.compare_digest(creds.username, user)
        ok_pw = secrets.compare_digest(creds.password, password)
        if not (ok_user and ok_pw):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
                headers={"WWW-Authenticate": 'Basic realm="briefing"'},
            )
        return creds.username

    return require_admin

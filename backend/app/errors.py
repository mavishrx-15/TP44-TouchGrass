"""Explicit scaffold response: no fake routes, weather or saved content."""

from typing import NoReturn

from fastapi import HTTPException


def feature_pending(feature: str) -> NoReturn:
    raise HTTPException(
        status_code=501, detail={"code": "feature_not_implemented", "feature": feature}
    )

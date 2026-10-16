"""Guard for routers that need a real data provider that is not connected.

These routers used to answer with numbers generated from a hash of the request
(traffic, authority, backlinks, ad spend). Nothing measured them, so they are
refused outright rather than shown to customers as data.
"""
from typing import NoReturn

from fastapi import Depends, HTTPException


def provider_required(message: str):
    """Router-level dependency that answers every request with 501 NOT_IMPLEMENTED."""

    def _refuse() -> NoReturn:
        raise HTTPException(status_code=501, detail={"code": "NOT_IMPLEMENTED", "message": message})

    return Depends(_refuse)

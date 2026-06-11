"""Shared HTTP utilities for Matryca Plumber."""

from __future__ import annotations

import urllib.request
from typing import Any


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """urllib opener handler that refuses HTTP redirects."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None

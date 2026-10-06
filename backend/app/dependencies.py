"""Shared HTTP dependencies; feature modules must not import other routers."""

from typing import Annotated
from uuid import UUID

from fastapi import Header

DeviceId = Annotated[UUID, Header(alias="X-Device-ID")]

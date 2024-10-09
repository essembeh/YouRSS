from fastapi import APIRouter

from .. import __name__ as app_name
from .. import __version__ as app_version

router = APIRouter()


@router.get("/version")
async def version():
    return {"name": app_name, "version": app_version}

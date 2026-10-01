from fastapi import APIRouter

router = APIRouter(prefix="/auction", tags=["auction"])

# @router.get("/")
# async def 
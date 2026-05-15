from fastapi import APIRouter

router = APIRouter()

@router.post("/service/contact/create", status_code=201)
async def create_contact():
    return {"message": "success"}

from fastapi import APIRouter, status

router = APIRouter(
	tags = ["units"],
	responses = {status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
	prefix = "/sensor"
)

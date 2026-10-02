from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse

router = APIRouter(
	prefix="",
	tags=[],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.get("/privacy")
def privacy_policy():
	return RedirectResponse("https://github.com/Order-Of-The-Birb/ThunderAPI/README.md#privacy-policy", status.HTTP_301_MOVED_PERMANENTLY)

@router.get("/github", summary="Redirects to the github source code")
async def github_redirect():
    return RedirectResponse("https://github.com/Order-Of-The-Birb/ThunderAPI", status.HTTP_301_MOVED_PERMANENTLY)
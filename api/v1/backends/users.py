from tools import Request
from utils.auth import UserTokenCache
from api.v1.models.users import TerseReturnModel

async def get_terse(user:UserTokenCache.Entry, *userIds:int|str) -> dict[str, TerseReturnModel]:
	return await Request.send_template(
		user, 
		"get_users_terse_info",
		usersList = ";".join(str(i) for i in userIds)
	)

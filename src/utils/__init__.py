from utils.auth import AuthenticationError as AuthenticationError
from utils.auth import ServerAuth, UserAuth
from utils.news import NewsManager
from utils.vehicleParser import Vehicles

users_auth = UserAuth()
server_auth: ServerAuth | None = None # Start is deferred to app lifetime
vehicle_cache = Vehicles()
newsManager = NewsManager()

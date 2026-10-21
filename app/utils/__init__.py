from utils.auth import UserAuth, AuthenticationError, ServerAuth
users_auth = UserAuth()
server_auth: ServerAuth | None = None # Start is deferred to app lifetime

from utils.vehicleParser import Vehicles
vehicle_cache = Vehicles()

from utils.news import NewsManager
newsManager = NewsManager()

from utils.auth import UserAuth, AuthenticationError, ServerAuth
users_auth = UserAuth()
server_auth = ServerAuth()

from utils.vehicleParser import Vehicles # Must be after users_cache declaration, due to using users_cache
vehicle_cache = Vehicles()

from utils.news import NewsManager
newsManager = NewsManager()
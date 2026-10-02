
from utils.network import NetworkManager, NetworkError
networkManager = NetworkManager()

from utils.auth import UserAuth, AuthenticationError
users_cache = UserAuth(networkManager)

from utils.vehicleParser import Vehicles # Must be after users_cache declaration, due to using users_cache
vehicle_cache = Vehicles()

from utils.news import NewsManager
newsManager = NewsManager(networkManager)
from enum import IntEnum, Enum, auto
from re import search as re_search
from fastapi import HTTPException, status

class ServerPool(IntEnum):
	CHAR = 0
	INVENTORY = 1
	USERSTAT = 2
	CONTACTS = 3
	UGC = 4
	#region marketplace
	MARKET_JSON = 5
	MARKET_WEB = 6
	MARKET_CHAR = 7
	MARKET = 8
	MARKET_ASSET = 9
	#endregion
	VIEW_VEHICLE_PROXY = 10
	WALLET = 11
	
def getAction(action:str|None):
	if action is None:
		return None
	try:
		return Action[action]
	except KeyError:
		try:
			return UserAction[action]
		except KeyError:
			raise ValueError(f"Unknown action '{action}'. Available: {list(Action) + list(UserAction)}")
class Action(Enum): # Filtered actions, only leaving those that do not affect the account directly
	#region Char
	cln_get_users_terse_info = auto(), ServerPool.CHAR
	cln_get_leaderboard_json = auto(), ServerPool.CHAR  
	cln_clan_get = auto(), ServerPool.CHAR  
	ano_get_public_userstat = auto(), ServerPool.CHAR  
	cln_get_showcases = auto(), ServerPool.CHAR  
	cln_get_entitlements_price_ex = auto(), ServerPool.CHAR  
	cln_upd_entitlements_full = auto(), ServerPool.CHAR  
	cln_get_events_leaderboard = auto(), ServerPool.CHAR  
	cln_clan_get_leaderboard = auto(), ServerPool.CHAR  
	cln_clan_get_log = auto(), ServerPool.CHAR  
	cln_clan_find_by_prefix = auto(), ServerPool.CHAR  
	cln_get_price_ex = auto(), ServerPool.CHAR
	cln_require_unlock = auto(), ServerPool.CHAR
	cln_get_news_ex = auto(), ServerPool.CHAR
	ano_get_wishlist_json = auto(), ServerPool.CHAR
	#endregion
	#region Contact proxy
	cln_find_users_by_nick_prefix_json = auto(), ServerPool.CONTACTS
	#endregion
	#region User stat
	GetUnlocks = auto(), ServerPool.USERSTAT
	GetStats = auto(), ServerPool.USERSTAT
	GetUserStatDescList = auto(), ServerPool.USERSTAT
	#endregion
	#region UGC
	cln_get_ugc_items_info = auto(), ServerPool.UGC
	#endregion
class UserAction(Enum):
	#region Char
	cln_upgrade_crew = auto(), ServerPool.CHAR
	cln_set_research_clan_unit = auto(), ServerPool.CHAR
	cln_set_researchable = auto(), ServerPool.CHAR
	cln_train_aircraft = auto(), ServerPool.CHAR
	cln_add_to_wish_list = auto(), ServerPool.CHAR
	cln_remove_from_wish_list = auto(), ServerPool.CHAR
	cln_multi_consume_inventory_item_json = auto(), ServerPool.CHAR
	cln_set_current_booster = auto(), ServerPool.CHAR
	cln_bulk_train_aircraft = auto(), ServerPool.CHAR
	cln_buy_aircraft = auto(), ServerPool.CHAR
	cln_save_profile_showcase = auto(), ServerPool.CHAR
	cln_save_pilot_appearance = auto(), ServerPool.CHAR
	cln_select_title = auto(), ServerPool.CHAR
	cln_recycle_items = auto(), ServerPool.CHAR
	cln_inventory_purchase_item = auto(), ServerPool.CHAR
	cln_apply_spare_item = auto(), ServerPool.CHAR
	cln_clan_membership_request = auto(), ServerPool.CHAR
	ano_clan_accept_membership_request = auto(), ServerPool.CHAR
	ano_clan_dismiss_member = auto(), ServerPool.CHAR
	ano_clan_change_member_role = auto(), ServerPool.CHAR
	ano_clan_reject_membership_request = auto(), ServerPool.CHAR
	cln_clan_leave = auto(), ServerPool.CHAR
	cln_flush_clan_exp_to_unit = auto(), ServerPool.CHAR
	#endregion
	#region Contacts proxy
	GetContacts = auto(), ServerPool.CONTACTS
	cln_cs_login = auto(), ServerPool.CONTACTS
	#endregion
	#region Inventory Proxy
	GetItemDefsClient = auto(), ServerPool.INVENTORY
	GetInventory = auto(), ServerPool.INVENTORY
	GetItemPrices = auto(), ServerPool.INVENTORY
	ExchangeItems = auto(), ServerPool.INVENTORY
	#endregion
	#region Marketplace Proxy
	cln_filter_blocked_pairs = auto(), ServerPool.MARKET_JSON
	cln_get_app_tags = auto(), ServerPool.MARKET_WEB
	cln_market_info = auto(), ServerPool.MARKET_WEB
	cln_get_pair_stat = auto(), ServerPool.MARKET_WEB
	cln_books_brief = auto(), ServerPool.MARKET_WEB
	cln_get_user_history = auto(), ServerPool.MARKET_WEB
	cln_get_user_open_orders = auto(), ServerPool.MARKET_WEB
	cln_market_sell = auto(), ServerPool.MARKET_WEB
	cln_market_buy = auto(), ServerPool.MARKET_WEB
	cln_market_search = auto(), ServerPool.MARKET_WEB
	cln_market_get_asset_class = auto(), ServerPool.MARKET_WEB
	cln_get_general_blk = auto(), ServerPool.MARKET_CHAR
	cln_set_general_blk = auto(), ServerPool.MARKET_CHAR
	cmn_check_user_auth = auto(), ServerPool.MARKET
	cancel_order = auto(), ServerPool.MARKET
	GetContexts = auto(), ServerPool.MARKET_ASSET
	GetContextContents = auto(), ServerPool.MARKET_ASSET
	GetAssetClassInfo = auto(), ServerPool.MARKET_ASSET
	market_view_item = auto(), ServerPool.VIEW_VEHICLE_PROXY
	#endregion
	GetBalance = auto(), ServerPool.WALLET

class GaijinErrorCodes(Enum): # TODO: Finish documenting gaijin error codes
	# Will require a lot of testing to finish
	"""Enum for Gaijin's error codes."""
	# HTTP code, error details
	CLAN_NOT_MEMBER = {
		"code": status.HTTP_403_FORBIDDEN, 
		"detail":"You are not a member of the given clan"
	} 
	CLAN_CANDIDATE_TIMEOUT = {
		"code": status.HTTP_400_BAD_REQUEST, 
		"detail":"You are already a candidate for this clan"
	}
	CLAN_YOU_HAVE_NO_RIGHT = {
		"code": status.HTTP_403_FORBIDDEN,
		"detail": "You do not have permission to do this action"
	}
	CLAN_USER_IS_NOT_CANDIDATE = {
		"code": status.HTTP_404_NOT_FOUND,
		"detail": "The given user is not an applicant"
	}
	DECLINE_TO_CREATE_NEW_PROFILE = {
		"code": status.HTTP_403_FORBIDDEN,
		"detail": "User doesn't exist"
	}
	CLAN_IS_NOT_EXISTS = {
		"code": status.HTTP_404_NOT_FOUND,
		"detail": "Searched clan doesn't exist"
	}
	CLAN_ALREADY_HAS_CLAN = {
		"code": status.HTTP_409_CONFLICT,
		"detail": "User is already in a squadron"
	}
	@staticmethod
	def parse(response: bytes) -> None:
		"""Parse a Gaijin error code string into a properly formatted `HTTPException`. Returns early if error is not found or not given"""
		code: str = response.decode("utf-8")

		try:
			match = re_search(r"!ERROR:(.*)", code.upper())
			if match is None: return

			err = GaijinErrorCodes[ match.group(1).strip() ]
			raise HTTPException(
				status_code=err.value["code"], 
				detail=err.value["detail"]
			)
		except KeyError:
			raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=code)

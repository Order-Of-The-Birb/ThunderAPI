from enum import IntEnum, Enum, auto
from typing import NamedTuple
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

class AuthLevel(IntEnum):
	SERVER = 0			# public — always use the server account
	USER_PREFERRED = 1	# user token if present, else server account
	USER = 2			# must be a real user session

class ActionInfo(NamedTuple):
	seq: int
	pool: ServerPool
	auth: AuthLevel = AuthLevel.USER

class Actions(Enum):
	#region Char
	cln_get_users_terse_info = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.SERVER)
	cln_get_leaderboard_json = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.SERVER)
	cln_clan_get = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.SERVER)
	ano_get_public_userstat = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.SERVER)
	cln_get_showcases = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.SERVER)
	cln_get_entitlements_price_ex = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.SERVER)
	cln_upd_entitlements_full = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_get_events_leaderboard = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.SERVER)
	cln_clan_get_leaderboard = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.SERVER)
	cln_clan_get_log = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER_PREFERRED)
	cln_clan_find_by_prefix = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.SERVER)
	cln_get_price_ex = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_require_unlock = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_get_news_ex = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.SERVER)
	ano_get_wishlist_json = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER_PREFERRED)
	cln_upgrade_crew = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_set_research_clan_unit = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_set_researchable = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_train_aircraft = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_add_to_wish_list = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_remove_from_wish_list = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_multi_consume_inventory_item_json = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_set_current_booster = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_bulk_train_aircraft = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_buy_aircraft = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_save_profile_showcase = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_save_pilot_appearance = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_select_title = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_recycle_items = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_inventory_purchase_item = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_apply_spare_item = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_clan_membership_request = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	ano_clan_accept_membership_request = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	ano_clan_dismiss_member = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	ano_clan_change_member_role = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	ano_clan_reject_membership_request = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_clan_leave = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	cln_flush_clan_exp_to_unit = ActionInfo(auto(), ServerPool.CHAR, AuthLevel.USER)
	#endregion
	#region Contact proxy
	cln_find_users_by_nick_prefix_json = ActionInfo(auto(), ServerPool.CONTACTS, AuthLevel.SERVER)
	GetContacts = ActionInfo(auto(), ServerPool.CONTACTS, AuthLevel.USER)
	cln_cs_login = ActionInfo(auto(), ServerPool.CONTACTS, AuthLevel.USER)
	#endregion
	#region Inventory Proxy
	GetItemDefsClient = ActionInfo(auto(), ServerPool.INVENTORY, AuthLevel.USER)
	GetInventory = ActionInfo(auto(), ServerPool.INVENTORY, AuthLevel.USER)
	GetItemPrices = ActionInfo(auto(), ServerPool.INVENTORY, AuthLevel.USER)
	ExchangeItems = ActionInfo(auto(), ServerPool.INVENTORY, AuthLevel.USER)
	#endregion
	#region User stat
	GetUnlocks = ActionInfo(auto(), ServerPool.USERSTAT, AuthLevel.USER)
	GetStats = ActionInfo(auto(), ServerPool.USERSTAT, AuthLevel.USER)
	GetUserStatDescList = ActionInfo(auto(), ServerPool.USERSTAT, AuthLevel.USER)
	#endregion
	#region UGC
	cln_get_ugc_items_info = ActionInfo(auto(), ServerPool.UGC, AuthLevel.SERVER)
	#endregion
	#region Marketplace Proxy
	cln_filter_blocked_pairs = ActionInfo(auto(), ServerPool.MARKET_JSON, AuthLevel.USER)
	cln_get_app_tags = ActionInfo(auto(), ServerPool.MARKET_WEB, AuthLevel.SERVER)
	cln_market_info = ActionInfo(auto(), ServerPool.MARKET_WEB, AuthLevel.SERVER)
	cln_get_pair_stat = ActionInfo(auto(), ServerPool.MARKET_WEB, AuthLevel.SERVER)
	cln_books_brief = ActionInfo(auto(), ServerPool.MARKET_WEB, AuthLevel.SERVER)
	cln_get_user_history = ActionInfo(auto(), ServerPool.MARKET_WEB, AuthLevel.USER)
	cln_get_user_open_orders = ActionInfo(auto(), ServerPool.MARKET_WEB, AuthLevel.USER)
	cln_market_sell = ActionInfo(auto(), ServerPool.MARKET_WEB, AuthLevel.USER)
	cln_market_buy = ActionInfo(auto(), ServerPool.MARKET_WEB, AuthLevel.USER)
	cln_market_search = ActionInfo(auto(), ServerPool.MARKET_WEB, AuthLevel.SERVER)
	cln_market_get_asset_class = ActionInfo(auto(), ServerPool.MARKET_WEB, AuthLevel.SERVER)
	cln_get_general_blk = ActionInfo(auto(), ServerPool.MARKET_CHAR, AuthLevel.USER)
	cln_set_general_blk = ActionInfo(auto(), ServerPool.MARKET_CHAR, AuthLevel.USER)
	cmn_check_user_auth = ActionInfo(auto(), ServerPool.MARKET, AuthLevel.USER)
	cancel_order = ActionInfo(auto(), ServerPool.MARKET, AuthLevel.USER)
	GetContexts = ActionInfo(auto(), ServerPool.MARKET_ASSET, AuthLevel.SERVER)
	GetContextContents = ActionInfo(auto(), ServerPool.MARKET_ASSET, AuthLevel.SERVER)
	GetAssetClassInfo = ActionInfo(auto(), ServerPool.MARKET_ASSET, AuthLevel.SERVER)
	market_view_item = ActionInfo(auto(), ServerPool.VIEW_VEHICLE_PROXY, AuthLevel.USER)
	GetBalance = ActionInfo(auto(), ServerPool.WALLET, AuthLevel.USER)
	#endregion

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
	CLAN_TOO_HIGH_MEMBER_ROLE_REQUESTED = {
		"code": status.HTTP_403_FORBIDDEN,
		"detail": "Too high role requested"
	}
	OBSOLETE_USER_PROFILE = {
		"code": status.HTTP_501_NOT_IMPLEMENTED,
		"detail": "Non-converted obsolete profile"
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

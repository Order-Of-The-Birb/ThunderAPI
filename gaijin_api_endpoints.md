# Gaijin's endpoints used ingame  
**Written for game version `2.55.1.88`**  
Many of the shown 'endpoints' are actually just requests to the given server, with a specific `action` header set  
This isn't an exhaustive list, these are just all I could find through inspecting HTTP traffic  
Not all endpoints shall be documented, as it would take forever to decode and document every single endpoint (and some of them are outright impossible to replicate, like `cln_accept_eula`)  
## Char server endpoints  
- These endpoints all have their root as a char server (example: https://char-lw-nl-005-5.warthunder.com/char)  
- The titles of the sections are to be used as an `action` header value to get the desired data  
- Every `POST` request must have a `token` header given for authentication  
### cln_get_users_terse_info  
- `POST` request  
- Headers  
	- `usersList` (user IDs separated by ';')  
### cln_bulk_set_gblk  
### cln_ww_global_status_short  
### cln_get_leaderboard_json  
### cln_clan_get  
### ano_get_public_userstat  
### cln_get_showcases  
### cln_get_entitlements_price_ex  
### cln_upd_entitlements_full  
### cln_get_events_leaderboard  
### cln_bq_put_batch_json  
### cln_get_short_user_info_jwt  
### cln_upgrade_crew  
### cln_clan_get_leaderboard  
- `POST` request  
- Request headers  
	- `shortMode` (`on` or abscent)  
	- `sortField` (`dr_era5_hist` for Squadron battles)  
	- `clanId` (To look up a specific squadron, abscent when looking at the actual leaderboard)  
	- `seasonOrdinalNumber`  
	- `start` (Index to start from)  
	- `count` (Amount to get at once)  
- Response  
	- `BLK format`  
### cln_set_research_clan_unit  
### cln_clan_get_log  
### cln_set_researchable  
### cln_train_aircraft  
### cln_update  
### cln_add_to_wish_list  
### cln_remove_from_wish_list  
### cln_multi_consume_inventory_item_json  
### cmn_get_bin  
### cln_set_current_booster  
### cln_bulk_train_aircraft  
### cln_buy_aircraft  
### cln_save_decals  
### cln_save_attachables  
### cln_find_users_by_nick_prefix_json  
### cln_save_profile_showcase  
### cln_save_pilot_appearance  
### cln_select_title  
### cln_recycle_items  
### cln_inventory_purchase_item  
### cln_apply_spare_item  
### cln_clan_find_by_prefix  
### ano_clan_accept_membership_request  
- `POST` request  
- Headers  
	- `userid` (Kicked user)  
	- `uidHint` (Applying user)  
	- `gameVersion`  
- Request form  
	- LZ4HC compressed BLK  
	- `_id` (Squadron ID)  
	- `role` (Level to get on join)  
- Response form  
	- "!OK"  
### ano_clan_dismiss_member  
- `POST` request  
- Headers  
	- `userid` (Kicked user)  
	- `uidHint` (Kicking officer)  
	- `gameVersion`  
- Request form  
	- LZ4HC compressed BLK  
	- `comments` (The message given with the dismissal)  
- Response form  
	- "!OK"  
### cln_clan_membership_request  
- `POST` request  
- Request form  
	- LZ4HC compressed BLK  
	- `_id` (Squadron ID to apply for)  
	- `comments` (game leaves it empty, adding a value doesn't show anything ingame)  
- Response form  
	- All user data  
	- `ClanTag`, `ClanName` are filled with the squadron's data, which can be used for checking whether applying was successful  
### ano_clan_change_member_role  
- `POST` request  
- Header  
	- `userid` (Member to change)  
- Request form  
	- LZ4HC Compressed  
	- `role` (Role index to set, e.g. 6 for Sergeant)  
- Response form  
	- "!OK"  
### ano_clan_reject_membership_request  
- `POST` request  
- Header  
	- `userid` (Applicant to reject)  
- Request body  
	- LZ4HC compressed BLK  
	- `_id` (Squadron ID)  
	- `comments`  
### cln_clan_leave  
- `POST` request  
- `LZ4HC` compressed  
- Request body  
	- `comment` (Game defaults to a value of `comment` aswell)  
### cln_get_initial_meta  
- `POST` request  
- Header  
	- `uidHint` (Account UID)  
- Body notes  
	- Sends a lot of info on the computer  
	- Sends 2 values that are computed dynamically, that I must add  
		- `uuid2` (SHA1 sum of the concatenated `/dev/disk/by-id/` entries that point (symlink) to the root partition, in raw `readdir` order)  
		- `uuid3` (SHA1 sum of the root partition's UUID, with a single trailing space, extracted from `/proc/cmdline`)  
- Response  
	- Sends a LOT of game data back  
	- Includes `remoteSuccessSaveAsyncTaskId`, which is used for authentication on some endpoints  
### cln_get_price_ex  
- `POST` request  
- Header  
	- `uidHint` (Account UID)  
### cln_set_general_blk  
- `POST` request  
- Header  
	- `uidHint` (Account UID)  
	- `appId` (Game ID, WT is 1067)  
### cln_get_ugc_items_info  
### cln_accept_eula  
- `POST` request  
- Header  
	- `uidHint` (Account UID)  
	- `returnOnlyEULA`  
### cln_require_unlock  
- `POST` request  
- Header  
	- `uidHint` (Account UID)  
### cln_set_starting_info  
- `POST` request  
- Header  
	- `uidHint` (Account UID)  
### cln_get_meta_blk  
- `POST` request  
- Header  
	- `uidHint` (Account UID)  
	- `appId` (Game ID, WT is 1067)  
### noa_bigquery_client_noauth  
### cln_get_binary_diff  
### cln_get_news_ex  
### ano_get_external_ids  
- `POST` request  
- Header  
	- `uidHint` (Self ID)  
	- `userid` (Lookup ID)  
### ano_get_wishlist_json  
- `POST` request  
- Header  
	- `uidHint` (Self ID)  
	- `userid` (Lookup ID)  
- Response form example  
	```json  
	{  
		"userId": 77753776,  
		"units": [  
			{  
			"unit": "us_xm1_gm",  
			"comment": "low tier abrooms",  
			"time": 1755869479  
			},  
			{  
			"unit": "us_xm1_chrysler",  
			"comment": "sadge, will never get due to console politics",  
			"time": 1755869501  
			}  
		]  
	}  
	```  
### cln_flush_clan_exp_to_unit  
### cln_save_weapon_presets  
## Contact proxy endpoints  
- Same as before (example: https://contact-proxy-02.gaijin.net/json)  
### cln_get_allowed_to_be_added_to_contacts  
- `POST` request  
- Returns JSON  
- Request form: `Not needed`  
- Response form:  
	```json  
	{  
		"ata": true  
	}  
	```  
	- No clue what this is meant to say  
### GetContacts  
- `POST` request  
- Returns JSON  
- Request form:  
	```json  
	{  
		"groups": ["warthunder"],  
		"id": id,  
		"jsonrpc": "2.0",  
		"method": "GetContacts",  
		"satus": [statuses]  
	}  
	```  
	- Yes it is actually called `satus`  
	- `satus`  
		- `requestsToMe`  
		- `meInBlacklist`  
- Response form:  
	```json  
	{  
		"warthunder": {  
			"approved": [  
				{  
					"uid": userID,  
					"nick": "nickname",  
					"time": UNIX timestamp,  
					"convNick": "nickname",  
					"isRequestor": bool  
				},  
				{...}  
			],  
			"myRequests": [...],  
			"rejectedByMe": [...],  
			"myBlacklist": [...]  
		}  
	}  
	```  
### cln_cs_login  
- `POST` Request  
- Returns JSON  
- Request body:  
	```json  
	{  
		"game":"wt"  
	}  
	```  
	- Sure i guess?  
- Response body:  
	```json  
	{  
		"chardToken": Some kind of token,  
		"user_id": user's ID,  
		"nick": "nickname",  
		"login": {  
			"first": UNIX timestamp,  
			"last": UNIX timestamp,  
		}  
	}  
	```  
### cln_find_users_by_nick_prefix_json  
## Inventory proxy endpoints  
- Same as before (example: https://inventory-proxy-01.gaijin.net/char)  
### GetItemDefsClient  
- `POST` request  
- Header  
	- `uidHint` (Self ID)  
	- `appId` (game ID, WT's is `1067`)  
- Response form example  
	```json  
	{  
		"response": {  
			"timestamp": 1777580655,  
			"itemdef_json": [  
				{  
					"Timestamp": "2022-07-22T10:05:55.0632171Z",  
					"alwaysPresent": false,  
					"auctionable": false,  
					"background_color": "",  
					"bundle": "2752032",  
					"deprecated": false,  
					"exchange": "2752030,2000000x3",  
					"expireAt": "",  
					"granted_by_purch": "",  
					"hidden": false,  
					"icon_url": "",  
					"icon_url_large": "",  
					"item_quality": 0,  
					"itemdefid": 2752031,  
					"lifetime": "1m",  
					"lifetime_modifier": "",  
					"limitOnPurchase": 0,  
					"market_hash_name": "",  
					"marketable": false,  
					"meta": "",  
					"name": "Sensors (unexamined working) 2752030 - Examine Process",  
					"name_color": "",  
					"premium": "",  
					"required_items": "",  
					"steam_itemdefid": 0,  
					"tags": "type:craft_process;isDisassemble:true;customLocalizationPreset:itemExamination",  
					"tradable_delay_sec": 0,  
					"type": "delayedexchange"  
				},  
				{  
					"Timestamp": "2022-07-22T10:05:55.0632171Z",  
					"alwaysPresent": false,  
					"auctionable": false,  
					"background_color": "",  
					"deprecated": false,  
					"description": "This item is unexamined. You need to examine it in order to understand whether it is defective or not.",  
					"exchange": "",  
					"expireAt": "2019-04-29T11:00:00Z",  
					"granted_by_purch": "",  
					"hidden": false,  
					"icon_url": "https://static-ggc.gaijin.net/events/craft_i180/craft_i180_left_aileron.png",  
					"icon_url_large": "https://static-ggc.gaijin.net/events/craft_i180/craft_i180_left_aileron.png",  
					"item_quality": 1,  
					"itemdefid": 2531430,  
					"lifetime": "",  
					"lifetime_modifier": "",  
					"limitOnPurchase": 0,  
					"market_hash_name": "",  
					"marketable": false,  
					"meta": "",  
					"name": "Left aileron",  
					"name_color": "AFAFA1",  
					"premium": "",  
					"required_items": "",  
					"steam_itemdefid": 0,  
					"tags": "type:craft_part;canBeDisassembled:mainAction;markingPreset:unexaminedItem;customLocalizationPreset:itemExamination;alwaysKnownItem:true;quality:common",  
					"tradable_delay_sec": 0,  
					"type": "item",  
					"used_to_create": "2531431"  
				},  
				{...}  
			]  
		}  
	}  
	```  
### GetInventory  
- `POST` request  
- Headers  
	- `uidHint` (User ID of person to check)  
	- `appid` (for WT it's `1067`)  
- Response form example  
	```json  
	{  
		"response": {  
			"item_json": [  
				{  
						"accountid": "126390297",  
						"appid": 1067,  
						"craftedFrom": "",  
						"expireAt": "",  
						"itemdef": 299004,  
						"itemid": "7059552941",  
						"origin": "external",  
						"quantity": 2,  
						"seenByPlayer": false,  
						"state": "none",  
						"timestamp": "2026-04-29T19:43:10.7254004Z",  
						"tradable_after_timestamp": "0"  
					},  
			]  
		}  
	}  
	```  
### GetItemPrices  
- `POST` request  
- Header  
	- `currency` (I had the value "WTS" when checking)  
	- `uidHint` (Self ID)  
- Response form  
	```json  
	{  
		"response": {  
			"itemPrices": [  
				{  
					"itemdefid": 216013,  
					"price": 50000  
				},  
				{  
					"itemdefid": 216019,  
					"price": 10000  
				},  
				{...}  
			]  
		}  
	}  
	```  
### ExchangeItems  
## User stat proxy endpoints  
- Same as before (example: https://userstat-proxy-01.gaijin.net/char)  
### GetUnlocks  
### GetStats  
### GetUserStatDescList  
## UGC Info proxy endpoints  
- Same as before (example: https://ugcinfo-proxy-01.gaijin.net/char)  
### cln_get_ugc_items_info  
- `POST` request  
- Request form example:  
	```json  
	{  
		"appId": 1067,  
		"guids": [  
			"9662f000-5a1e-406b-b033-52c0dfa43067",  
			"b312f000-5a1e-406b-b033-52c0dfa43067",  
			"dc62f000-5a1e-406b-b033-52c0dfa43067"  
		]  
	}  
	```  
	- WT has the appId of `1067`  
- Response form example:  
	```json  
	{  
		"9662f000-5a1e-406b-b033-52c0dfa43067": {  
			"provider_id": 997628,  
			"metaHash": "7sv5lmmpmm2anpb6h7rh4vjl6lykxzol-bwu",  
			"description_english": "JA37C, 101 squadron \"Johan Röd\", F10 air wing, Ängelholm, 2001\. Was painted in the red scheme to fly in a goodbye ceremony",  
			"author": 43916192,  
			"tags": "inGamePreview:yes;semihistorical:yes;eventName:camo_trophy_2_09;authenticity:semihistorical;country:sweden;vehicleType:aircraft;vehicleSubtypes:fighter;quality:junk;type:skin;approved:yes",  
			"name_english": "JA37C 'The Show Must Go On'",  
			"icon_url": "https://wt-ugc.cdn.gaijin.net/dc/me/ez735w7myvqyw5iqdmeufxkh4web-bcqv.icon.jpg",  
			"appId": 1067,  
			"provider": "live",  
			"author_name": "StarlightShinin",  
			"description_russian": "JA37C, 101-я эскадрилья \"Johan Röd\", авиакрыло F10, Энгельхольм, 2001\. Был окрашен в красный цвет для \nцеремонии вывода AJS-37 из состава ВВС Швеции",  
			"type": "skin",  
			"meta": "bmFtZTp0PSJ1c2VyIg0KbW9kZWxOYW1lOnQ...",  
			"link": "https://live.warthunder.com/post/997628/",  
			"item_quality": 2,  
			"name_color": "14BD3A",  
			"name_russian": "JA37C 'The Show Must Go On'",  
			"background_color": "000000",  
			"icon_url_large": "https://wt-ugc.cdn.gaijin.net/5o/5w/eywlcndkrqojcxuiq35kmpl7qplx-cjac.icon_large.jpg"  
		},  
		"b312f000-5a1e-406b-b033-52c0dfa43067": {  
			"provider_id": 1090807,  
			"metaHash": "ibyaykxkwjmntrsxuwotlfbtafgnfdl5-66",  
			"description_english": "JAS39A 'Prototype 39-2', Aeroseum in Göteborg in February 2023",  
			"author": 2456465,  
			"tags": "inGamePreview:yes;historical:yes;eventName:camo_trophy_2_33;authenticity:historical;country:sweden;vehicleType:aircraft;vehicleSubtypes:fighter;type:skin;approved:yes",  
			"name_english": "JAS39A 'Prototype 39-2'",  
			"icon_url": "https://wt-ugc.cdn.gaijin.net/3q/z6/6w6xvwxqrlswz5fany2cnwiszc4x-baoh.icon.jpg",  
			"appId": 1067,  
			"provider": "live",  
			"author_name": "Atsuk0",  
			"description_russian": "JAS39A \"Прототип 39-2\", Музей ВВС Aeroseum в Гетеборге, февраль 2023 года",  
			"type": "skin",  
			"meta": "bmFtZTp0PSJ1c2VyIg0KbW9kZWxOYW1lOnQ9InNhYWJfamFzMzl...",  
			"link": "https://live.warthunder.com/post/1090807/",  
			"item_quality": 2,  
			"name_color": "14BD3A",  
			"name_russian": "JAS39A 'Прототип 39-2'",  
			"background_color": 0,  
			"icon_url_large": "https://wt-ugc.cdn.gaijin.net/vx/jx/y7dj2rm3rr2zu4jdkarnu6se7uiy-cemy.icon_large.jpg"  
		},  
		"dc62f000-5a1e-406b-b033-52c0dfa43067": {  
			"provider_id": 937249,  
			"metaHash": "nheqbp77gsephkb2ew4ht5vn24ltnqgm-bsx",  
			"description_english": "M60, 33rd Armor Regiment",  
			"author": 341717,  
			"tags": "thunderleague:yes;inGamePreview:yes;historical:yes;authenticity:historical;country:usa;vehicleType:tank;vehicleSubtypes:medium_tank;type:skin;approved:yes",  
			"name_english": "M60, 33rd Armor Regiment",  
			"icon_url": "https://wt-ugc.cdn.gaijin.net/wg/n6/c7mvwzidcjqiaf2vddugzltnubks-clvr.icon.jpg",  
			"appId": 1067,  
			"provider": "live",  
			"author_name": "ItssLuBu",  
			"description_russian": "M60, 33-й Танковый Полк",  
			"type": "skin",  
			"meta": "bmFtZTp0PSJ1c2VyIg0KbW9kZWxOYW1lOnQ9InVzX202MCINC...",  
			"link": "https://live.warthunder.com/post/937249/",  
			"item_quality": 1,  
			"name_color": "FFFFFF",  
			"name_russian": "M60, 33-й Танковый Полк",  
			"background_color": 0,  
			"icon_url_large": "https://wt-ugc.cdn.gaijin.net/pr/65/44j24o3mc4b7wu7a4wxltod3sn6w-fu7r.icon_large.jpg"  
		}  
	}  
	```  
## Yupmaster endpoints  
- Queries done by the in-house launcher of gaijin  
- The root of these endpoints are all `https://yupmaster.gaijinent.com`  
### /launcher/version.php  
- `GET` request  
- Query parameters  
	- `app_id` (The app to get the version of)  
	- `ver` (Current version, optional)  
- Query parameter examples  
	- `app_id`  
		- `WarThunderLauncherLinux`  
		- `PromoWarThunderMain`  
- Response  
	- A single string, containing the version number  
		- E.g. `1.0.3.40` (launcher) or `2.55.1.56` (wt) as of writing  
		- The WT version is **not** the current downloaded version  
### /launcher/cdn_conf.php  
- `GET` request  
- Query parameters  
	- `proj` (The app to get the version of, in this case `warthunder`)  
- Response  
	- A JSON containing data about different seed URLs and trackers  
### /yuitem/get_version.php  
- `GET` request  
- Query parameters  
	- `proj` (The app to get the version of)  
	- `tag`  
- Query parameter examples  
	- `proj`  
		- `warthunder`  
	- `tag`  
		- `[no content]` (production version)  
		- `dev` (dev version)  
		- `dev-stable` (dev_stable version)  
- Response  
	- A single string, containing the version number (e.g. `2.55.1.88` as of writing)  
	- This version is the actual, downloaded version  
### /launcher/update.php  
- `GET` request  
- Query parameters  
	- `app_id` (For wt it is `PromoWarThunderMain`)  
	- `consist` (The launcher just sends a value of `1`)  
	- `ver` (URL safe version of currently downloaded version)  
- Response  
	- Some sort of token in the first line  
	- Second line is an URL to downloading the .zip of the update  
## Marketplace endpoints  
- The titles of the sections are to be used as an `action` form value to get the desired data, unless specified otherwise  
- Every `POST` request must have a `token` form value for authentication  
- Every `POST` request must have an `appId` value given (`1067` is WT)  
### json  
- All endpoints in this category point to `https://market-proxy.gaijin.net/json`  
#### cln_filter_blocked_pairs  
- `POST` request  
- Form data  
	- `transactid`  
	- `reqstamp`  
	- `list` (array of dicts)  
		- `appId` (`1067` for WT)  
		- `marketName` (e.g. `id100150_tusk_force_trophy`)  
- Response (array of dicts)  
	- `appId`  
	- `marketName`  
	- `mode`  
	- `affectAfterSec`  
### web  
- All endpoints in this category point to `https://market-proxy.gaijin.net/web`  
#### cln_get_app_tags  
- `POST` request  
- Host `https://market-proxy.gaijin.net/web`  
- Form data  
	- `count` (items per page)  
	- `skip` (for pagination)  
	- `country`  
#### cln_market_info  
- `POST` request  
- Form data  
	- `token`  
	- `action`  
- Gets metadata about marketplace actions  
	- Gaijin's fee  
	- min/max possible price  
	- min/max auction duration  
	- supported games  
#### cln_get_pair_stat  
- `POST` request  
- Form data  
	- `market_name` (essentially `id100148_leviathans_trophy` from the url `https://trade.gaijin.net/market/1067/id100148_leviathans_trophy?assetId=6106171621`)  
	- `currencyid` (`gjn`)  
- Gets the price graph  
- Returns an dict  
	- `1d` (`Whole time` graph)  
	- `1h` (`Short range` graph)  
	- Each one has a list of arrays attached  
		- i[0] is timestamp  
		- i[1] is price (*10000)  
		- i[2] is amount placed on marketplace  
#### cln_books_brief  
- `POST` request  
- Form data  
	- `market_name` (same as before)  
- Response  
	- `type`  
	- `BUY`  
	- `SELL`  
	- `depth`  
	- `BUY` and `SELL` are arrays of arrays  
		- i[0] is price (*10000)  
		- i[1] is quantity  
	- `depth` is a dict which shows how many total orders are there  
		- `BUY` - Buy orders  
		- `SELL` - Sell orders  
#### cln_get_user_history  
- `POST` request  
- Form data  
	- `count` (how many per request)  
	- `skip` (for pagination)  
- Response  
	- `events` is an array of dicts  
		- `id`  
		- `ts` (timestamp)  
		- `count`  
		- `price`  
		- `cancelReason` (when applicable)  
		- `currency` (`gjn`)  
		- `dealUid`  
		- `orderId`  
		- `event`  
			- `cancel`  
			- `new`  
			- `deal`  
		- `type` (`SELL` or `BUY`)  
		- `appid` (`1067` for WT)  
		- `hashname`  
		- `auction`  
		- `seen`  
#### cln_get_user_open_orders  
#### cln_market_sell  
- `POST` request  
- Form data  
	- `transactid`  
	- `reqstamp` (request timestamp)  
	- `appid` (`1067` for WT)  
	- `contextid` (`1`)  
	- `assetid` (ID from inventory)  
	- `amount` (int in a string)  
	- `currencyid` (`gjn`)  
	- `price` (x/10000 for GJN)  
	- `seller_should_get` (x/10000 for GJN)  
	- `agree_stamp` (timestamp)  
	- `privateMode` (appear as anonymous, boolean)  
#### cln_market_buy  
- `POST` request  
- Form data  
	- `transactid`  
	- `reqstamp` (request timestamp)  
	- `appid` (`1067` for WT)  
	- `market_name` (hash name of the vehicle/item)  
	- `amount`  
	- `currencyid` (`gjn`)  
	- `price` (x/10000 for GJN)  
	- `agree_stamp` (timestamp)  
	- `privateMode` (appear as anonymous, boolean)  
#### cln_market_search  
- `POST` request  
- Form data  
	- `count` (Amount per request)  
	- `skip` (for pagination)  
	- `text` (For direct searching, leave as empty string for all)  
	- `options` (`;` separated tags)  
		- `any_sell_orders`  
		- `any_buy_orders`  
		- `include_marketpairs`  
	- `appid_filter` (`1067` for WT, `appId` can be omitted here)  
- Response  
	- `assets` contains the vehicle data, it is an array of dicts  
		- `appid` (basically always `1067` if you filter by it)  
		- `hash_name` (e.g. `id10051_heavy_cavalry_key`)  
		- `name` (display name, `'Heavy Cavalry' key`)  
		- `commodity` (boolean value)  
		- `icon` (vehicle icon URL)  
		- `price` (lowest sell price *100 000 000)  
		- `buyprice` (highest buy price *100 000 000)  
		- `buydepth` (amount of buy orders)  
		- `tags` (array of tags)  
			- `type:(.+)`  
			- `quality:(.+)`  
			- `countryDenyPurchase:be_kr_br`  
			- `eventName:(.+)`  
			- `country:(.+)`  
			- `inGamePreview:yes`  
		- `asset_class` (array of dicts)  
			- `name`  
				- `__itemdefid`  
			- `value` - Vehicle ID (e.g. `"50068"`)  
		- `color` (HEX value for the background, e.g. `C816C1` for epic items)  
#### cln_market_get_asset_class  
- `POST` request  
- Form data  
	- `name` (hash name)  
- Response  
	- `asset_class` is an array of dicts  
		- `name` (`__itemdefid`)  
		- `value` (int in a string, e.g. `"100150"`)  
### char  
- All endpoints in this category point to `https://market-proxy.gaijin.net/char`  
#### cln_get_general_blk  
- `POST` request  
- Headers  
	- `token`  
	- `blkType`  
		- `GBT_GENERAL_SETTINGS`  
		- `FAVORITES`  
- Returns values based on the `blkType` header  
#### cln_set_general_blk  
- `POST` request  
- Used for setting the values in `cln_get_general_blk`  
- Headers  
	- `token`  
	- `blkType`  
		- Same as previously  
- Form data (dict)  
	- `favorites` (array of dicts)  
		- `appId` (`1067` for WT)  
		- `hashName`  
		- `dateAdded` (date when favorited, UTC time)  
- Response: `!OK`  
### market  
- All endpoints in this category point to `https://market-proxy.gaijin.net/market`  
#### cmn_check_user_auth  
- `POST` request  
- Host `https://market-proxy.gaijin.net/market`  
- Returns metadata about the logged in user, for example  
	- `mail`  
	- `nick`  
	- `roles` (e.g. `CLIENT` and `ANONYMOUS`)  
	- `userId`  
#### cancel_order  
- `POST` request  
- Form data  
	- `transactid`  
	- `reqstamp`  
	- `pairId`  
	- `orderId`  
### assetAPI  
- All endpoints in this category point to `https://market-proxy.gaijin.net/assetAPI`  
#### GetContexts  
- `POST` request  
- Gives some kind of "context" that can be used in `GetContextContents`  
- Form data  
	- `appid` (`1067`)  
- Response format  
	- Useless overhead (`result>contexts`)  
	- Result is mostly a list of dicts  
		- `asset_count`  
		- `id` (value to be used as `contextid`)  
		- `name`  
		- `nested`  
		- `user_facing`  
#### GetContextContents  
- `POST` request  
- Form data  
	- `contextid`  
- Gets the contents of your inventory  
#### GetAssetClassInfo  
- `POST` request  
- Form data  
	- `class_name0` (`__itemdefid`)  
	- `class_value0` (vehicle ID)  
	- `class_count` (no clue what this is supposed to be)  
- Gets data about the marketplace item  
### market_view_item  
- `POST` request  
- Host `https://login.gaijin.net/proxy/api/matching/notifyClient`  
- Headers  
	- `Authorization` (Bearer {insert token})  
- Form data  
	- `action` (`market_view_item`)  
	- `params`  
		- `appId` (`1067` for WT)  
		- `assetClass` (array of dicts)  
			- `name` (value of `class_name0`)  
			- `value` (value of `class_value0`)  
### GetBalance  
- `GET` request  
- `Authorization: Bearer {token}` header for auth  
- Host `https://wallet.gaijin.net/GetBalance`  
- Response format  
	- `status` (`OK`)  
	- `user_id`  
	- `balance` (GJN *10000)  
## Replay endpoints  
### https://wt-replays-cdnnow.cdn.gaijin.net/{match ID HEX}/xxxx.wrpl  
- `GET` request  
- Requires no authentication  
- Returns a `wrpl` file  
### https://warthunder.com/en/api/replay  
- `POST` request  
- Request body  
	- `findMissionValue`  
	- `findUserType`  
		- `USERNAME`  
		- `ID`  
	- `findUserValue` (what to search)  
	- `gameMode` (array of values)  
		- `arcade`  
		- `realistic`  
		- `simulation`  
	- `gameType`  
		- `randomBattle`  
		- `squadron_tournament`  
		- `clanBattle`  
		- `tournaments`  
	- `isUserOwnReplays`  
	- `limit` (how many per page)  
	- `page` (pagination)  
	- `rankRange`  
	- `techType`  
		- `all`  
		- `aircraft`  
		- `helicopter`  
		- `tank`  
		- `ship`  
		- `mixed`  
	- `timeRangeFrom`  
	- `timeRangeFromDay` (int)  
	- `timeRangeFromMonth` (int)  
	- `timeRangeFromTime` (%H:%M formatted string)  
	- `timeRangeTo`  
	- `timeRangeToDay`  
	- `timeRangeToMonth`  
	- `timeRangeToTime` (same as before)  
## Other endpoints  
### https://auth.gaijinent.com/login.php  
- `POST` request  
- Request form:  
	```json  
	{  
		"client":"unknown_",  
		"game":"wt",  
		"gapp_id":79,  
		"login": "<email>",  
		"meta": 1,  
		"password": "<password>",  
		"v":2,  
		"2step": 999999  
	}  
	```  
	Optional data:  
	- `client` (Probably used for tracking logins)  
	- `gapp_id` (unsure what this does, probably used for tracking logins)  
	- `meta` (only sends metadata, such as creation location, CC URL used, registration IP, etc.)  
	- `v` (Unsure what this does)  
	- `2step` (2FA verification code)  
- Response form schema:  
	```json  
	{  
		"auth": "login",  
		"country": "country tag",  
		"gjnick": "gaijin nickname",  
		"jwt": "token",  
		"lang": "language",  
		"level": "normal",  
		"login": "email used",  
		"nick": "war thunder nickname",  
		"nickorig": "original wt nickname",  
		"status": "OK",  
		"tags": "tags associated with user (e.g. 'email_verified' or 'customer' (yes this exists))",  
		"token": "access token to most parts of the internally used API",  
		"token_exp": "expiration of the token from now in seconds (usually an hour)",  
		"user_id": "the gaijin store ID of the user"  
	}  
	```  
	- No example due to privacy issues with just copy pasting  
	- Using `meta` adds more info, which can vary a lot so I am not documenting that part  
	- The following keys have been found to have the following values that can be assigned  
		- `auth`  
			- `login` (if no 2FA)  
			- `2step` (if 2FA is set up)  
		- `level`  
			- `fastregister`  
			- `normal`  
		- `tags`  
			- `email_verified`  
			- `2step`  
			- `2step_totp`  
			- `customer` (purchased anything in the gaijin shop)  
			- `customer_wt` (purchased anything for WT in gaijin shop)  
			- `customer_el` (purchased anything for Enlisted in gaijin shop)  
			- `gjpass` (account uses gaijin pass)  
			- `google` (account uses google authenticator?)  
			- `liveclone` (account migrated from Xbox to PC)  
			- `player_wt` (has WT account)  
			- `player_wtm` (has WT Mobile account)  
			- `player_el` (has Enlisted account)  
			- `partner_unknown` (?)  
			- `partner_organic` (?)  
			- `phone_verified`  
			- `sso`  
			- `sso_allowed_post`  
			- `steam_el` (Played Enlisted on steam?)  
			- `wt_first_login` (logged in before?)  
			- `wt_quiz_success` (no clue)  
			- `infantry_cbt_requester` (probably a temporary flag, requested Infantry CBT participation)  
			- `lang_*` (computer locale on account creation?)  
### https://auth.gaijinent.com/login_token.php  
- `POST` request  
- Request form  
	- `token` (The token you aquire through logging in normally)  
- Same as the `login.php` in response format  
- The endpoint extends the lifetime of the token  
- The game usually calls this endpoint every 30 minutes  
### https://auth.gaijinent.com/api/auth/requestTwoStep  
- `GET` request  
- Query parameters  
	- `requestId` - Obtained from `login.php`  
	- `userId` - Obtained from `login.php`  
- Doesn't return anything really  
	- If user doesn't respond in time the socket hangs up  
	- If it hangs up the game usually sends another `login.php` and uses the new `requestId` from that  
- Response form  
	- `State`  
	- `UserId` (The same as provided)  
	- `Device` (Some sort of device ID)  
	- `Request` (Same as provided)  
	- `Message` (The 2FA code)  
	- `v` (No clue lmao)  
### https://static-ggc.gaijin.net/units/*.png  
- GET request  
- the `*` must be replaced with the internal name of a vehicle you want (e.g. "https://static-ggc.gaijin.net/units/uk_churchill_avre.png")  
### Newsfeed endpoints  
#### https://newsfeed.gap.gaijin.net/api/patchnotes/warthunder/en/  
- `GET` request  
- GET parameters  
	- `game`  
		- `warthunder`  
	- `platform`  
		- `pc` (Windows)  
		- `linux64`  
		- `ps4`  
		- `xbox`  
	- `page` (zero-indexed)  
	- `limit`  
	- `offset`  
- Response form:  
	- `status` (HTTP Status code)  
	- `result` (An array of dicts)  
		- `title`  
		- `rev`  
		- `tags` (Array of strings)  
			- ``  
		- `pinned` (bool as an int)  
		- `thumb` (URL to thumbnail)  
		- `customData`  
		- `kind`  
			- `patchnote`  
			- `minor`  
			- `major`  
			- `news`  
		- `version`  
			- Value is game version  
			- Only shows up under `minor` and `major` news  
		- `date`  
			- ISO formatted datetime string  
		- `alwaysShowPopup`  
		- `targets` (array of values)  
			- `game`  
		- `id`  
		- `titleShort` (Internal code for news entry)  
#### https://newsfeed.gap.gaijin.net/api/patchnotes/warthunder/en/{news_id}  
- `GET` request  
- `news_id` is the ID returned by the previous endpoint  
- Gives details about a specific news entry  
- Return format  
	- The values that match names with the previous version, share the same values, unless specified otherwise  
	- `status`  
	- `result`  
		- `title`  
		- `rev`  
		- `tags`  
		- `pinned`  
		- `thumb`  
		- `customData`  
		- `kind`  
		- `titleshort`  
		- `alwaysShowPopup`  
		- `targets`  
		- `date`  
		- `content`  
			- Array of dicts, that dictate how to format the news (HTML-ish format)  
			- Can be used to retrieve useful information out of news articles (e.g. event start, details, etc.)  
		- `type`  
		- `version`  
### https://api.gaijinent.com/item_info.php  
- `POST` request  
- Returns JSON  
- Gets premium/event vehicle data  
- Request form:  
	- `guids[]=[guid]` repeated for every single item  
		- Example guid: 009FB77B-92F8-41B7-9307-D6B834AFB345 (VL Pyorremyrsky Pack)  
	- `special=1`  
	- `jwt`  
- Response form:  
	```json  
	{  
		"status": "OK",  
		"items": {  
			"009FB77B-92F8-41B7-9307-D6B834AFB345": {  
				"item_id": "7173",  
				"title": "VL Pyorremyrsky Pack",  
				"url": "https://store.gaijin.net/story.php?id=7173",  
				"short_desc": null,  
				"multi_purch": false,  
				"status": "discard",  
				"shop_price": 19.99,  
				"shop_price_curr": "eur",  
				"can_be_bought": false,  
				"actions": [],  
				"price_usd": 19.99  
			},  
			"0108E1C9-6A59-4838-A67D-1CD8004DACA0": {  
				"item_id": "6553",  
				"title": "Semovente 105/25 Pack",  
				"url": "https://store.gaijin.net/story.php?id=6553",  
				"short_desc": null,  
				"multi_purch": false,  
				"status": "discard",  
				"shop_price": 24.99,  
				"shop_price_curr": "eur",  
				"can_be_bought": false,  
				"actions": [],  
				"price_usd": 24.99  
			},  
			{...}  
		}  
	}  
	```  
	- The following keys have been found to have the following values that can be assigned  
		- `status`  
			- `discard` (GE vehicle)  
			- `publisher` (Pack vehicle)  
### https://api.gaijinent.com/user_stoken.php  
- `POST` request  
- Request body  
	- `jwt`  
	- `token`  
- Response body  
	- `status` (`OK`)  
	- `stoken`  
	- `user_id`  
### https://api.gaijinent.com/login_stoken.php  
- `POST` request  
- Request body  
	- `stoken` (Token obtained from previous version)  
- Response body  
	- `auth`  
	- `country`  
	- `gjnick`  
	- `lang`  
	- `level`  
	- `login` (login email)  
	- `nick`  
	- `nickorig`  
	- `status` (`OK`)  
	- `tags` (comma separated tags of the account)  
	- `token`  
	- `token_exp`  
	- `user_id`  
	- `jwt`  

### https://login.gaijin.net/en/sso/getShortToken  
## Endpoints not used ingame  
### http://newslist.gaijin.net:8080/news/{game}/en/js  
- `GET` request  
- Special thanks to SnailBot's source code, where the URL was found  
- GET parameters  
	- `game`  
		- `warthunder`  
		- `crossout`  
		- `starconflict`  
	- `offset`  
- RSS feeds of this page  
	- http://newslist.gaijin.net:8080/news/warthunder/en/rss  
	- http://newslist.gaijin.net:8080/news/warthunder/en/atom  
### https://warthunder.com/en/community/getclansleaderboard/dif/_hist/page/\[pagenum\]/sort/dr_era5  
## Useful info through webscraping (no direct API)  
### https://warthunder.com/en/game/changelog/  
### https://forum.warthunder.com/t/season-schedule-for-squadron-battles/4446  

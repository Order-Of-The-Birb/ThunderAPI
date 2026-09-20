from os import getenv
from typing_extensions import Annotated
from typing import Any
from random import randint
from datetime import datetime, UTC
from fastapi import APIRouter, Query, Path, Request as faRequest, HTTPException, status

from tools import Request
from utils.helper import dtToTimestampMs
from api.shared import limiter
from api.v1.shared import TokenBearer
from api.v1.backends.marketplace import item_in_inventory, get_inventory
from api.v1.models.marketplace import SellModel, ItemModel
from api.v1.models.base import GenericEmptyResponse

router = APIRouter(
	prefix="/market",
	tags=["marketplace"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.post(
	"/sell/{itemHash}",
	summary="Puts up a sell order for the given `itemHash`",
	responses={
		status.HTTP_200_OK: {"description": "Sell order has successfully been placed", "model": list[SellModel]},
		status.HTTP_400_BAD_REQUEST: {"description": "Count is too high"},
		status.HTTP_404_NOT_FOUND: {"description": "Item could not be found in the inventory"}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def sell_item(
	request: faRequest, user: TokenBearer,
	itemHash: Annotated[str, Path(description="The item's hash value")],
	price: Annotated[float, Query(description="The price in GJN to sell for (Includes gaijin's fee, not the value you get)", ge=0.1, le=2000)], 
	count: Annotated[int, Query(description="The amount to sell at once", gt=0)] = 1,
	anonymous: Annotated[bool, Query(description="Appear as an anonymous seller")] = False
):
	agree_stamp = dtToTimestampMs(datetime.now(UTC))

	itemsInInv = await item_in_inventory(user, itemHash)
	if itemsInInv is None:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found in inventory")
	if len(itemsInInv.ids) < count:
		raise HTTPException(status.HTTP_400_BAD_REQUEST, "Count is higher than the items in inventory")

	price = price
	gaijin_fee = price*0.15
	seller_should_get = price-gaijin_fee

	solditems = []
	for i in range(count):
		assetId = itemsInInv.ids.pop()
		resp = await Request.send_template(
			user,
			"cln_market_sell",
			transactid = randint(10**6, 10**15),
			reqstamp = dtToTimestampMs(datetime.now(UTC)),
			assetid = assetId,
			amount = 1,
			price = int(price*10000),
			seller_should_get = int(seller_should_get*10000),
			agree_stamp = agree_stamp,
			privateMode = anonymous,
			contextid = itemsInInv.contextid
		)
		solditems.append({
			"item": assetId,
			"success": "response" in resp and resp["response"].get("success", False),
			"price": price,
			"seller_gets": seller_should_get
		})
	return solditems

@router.post(
	"/buy/{itemHash}",
	summary="Puts up a buy order for the given `itemHash`",
	responses={
		status.HTTP_200_OK: {"description": "The buy order has successfully been placed", "model": GenericEmptyResponse},
		status.HTTP_400_BAD_REQUEST: {"description": "Something prevented the buy order from being placed"},
		status.HTTP_403_FORBIDDEN: {"description": "Not enough funds"},
		status.HTTP_404_NOT_FOUND: {"description": "The given item doesn't exist"}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def buy_item(
	request: faRequest, user: TokenBearer,
	itemHash: Annotated[str, Path(description="The item's hash value")],
	price: Annotated[float, Query(description="The price in GJN to buy for", ge=0.1, le=2000)], 
	count: Annotated[int, Query(description="The amount to buy", gt=0)] = 1,
	anonymous: Annotated[bool, Query(description="Appear as an anonymous buyer")] = False
) -> GenericEmptyResponse:
	agree_stamp = dtToTimestampMs(datetime.now(UTC))
	resp = await Request.send_template(
		user,
		"cln_market_buy",
		transactid = randint(10**6, 10**15),
		reqstamp = dtToTimestampMs(datetime.now(UTC)),
		market_name = itemHash,
		amount = count,
		price = int(price*10000),
		agree_stamp = agree_stamp,
		privateMode = anonymous
	)
	if "response" not in resp:
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "An unexpected error occurred")
	resp = resp["response"]
	if "error" in resp:
		if resp["error"] == "ASSET_NOT_FOUND":
			raise HTTPException(status.HTTP_404_NOT_FOUND, "Item doesn't exist")
		elif "details" in resp and resp["details"] == "NOT_ENOUGH_FUNDS":
			raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough funds")
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, resp["error"])     
	if resp.get("success", False):
		return {
			"success": True
		}
	raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to put up buy order")

@router.get(
	"/inventory",
	summary="Gets the account's inventory contents"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def getInventory(
	request: faRequest, user: TokenBearer
):
	inv = await get_inventory(user)
	return [i.to_json() for i in inv]

@router.get(
	"/balance",
	summary="Gets the account's balance"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_balance(
	request: faRequest, user: TokenBearer
) -> float:
	data = await Request.send_template(
		user,
		"GetBalance"
	)
	if data.get("status") == "OK":
		return data["balance"]/10000
	raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get balance")

@router.get(
	"/search",
	summary="Searches the marketplace for a given item",
	responses={
		status.HTTP_200_OK: {"model": list[ItemModel]}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def searchItem(
	request: faRequest, user: TokenBearer,
	name: Annotated[str, Query(title="The item to search for. Leave empty to search for ALL units")] = "",
	count: Annotated[int, Query(title="Amount to get at once")] = 25,
	page: Annotated[int, Query(title="Pagination page. Works based off of `count`")] = 0,
):
	data = await Request.send_template(
		user,
		"cln_market_search",
		count = count,
		skip = count*page,
		text = name
	)
	if "response" in data:
		data:list[dict[str, Any]] = data["response"]["assets"]
	else:
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not get item data")
	for item in data:
		item["sell_price"] = item["price"] / 100000000
		item["buy_price"] = item["buy_price"] / 100000000
		item.pop("price")

		item["sell_orders"] = item["depth"]
		item["buy_orders"] = item["buy_depth"]
		item.pop("depth")
		item.pop("buy_depth")

		item.pop("appid")
		item.pop("color")
		item.pop("asset_class")

		new_tags = {}
		for tag in item["tags"]:
			tag:str
			if tag.count(":") != 1:
				... # TODO: Figure out something here
				return
			key, value = tag.split(":")
			if value == "yes":
				new_tags[key] = True
			elif value == "no":
				new_tags[key] = False
			else:
				new_tags[key] = value
		item["tags"] = new_tags
		del new_tags

	return data

@router.get(
	"/{itemHash}/orders/history",
	summary="Retrieves marketplace history data about the given item"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_item_history(
	request: faRequest, user: TokenBearer,
	itemHash: Annotated[str, Path(title="The item to look up")],
):
	pairData = await Request.send_template(
		user,
		"cln_get_pair_stat",
		market_name = itemHash
	)
	if "response" in pairData:
		pairData = pairData["response"]
	else:
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "An unexpected error occurred")

	ret_data = {
		"short":[],
		"whole":[]
	}
	for i in pairData["1h"]:
		ret_data["short"].append({
			"timestamp": i[0],
			"price": i[1]/10000,
			"transactions_count": i[2]
		})
	for i in pairData["1d"]:
		ret_data["whole"].append({
			"timestamp": i[0],
			"price": i[1]/10000,
			"transactions_count": i[2]
		})
	return ret_data

@router.get(
	"/{itemHash}/orders",
	summary="Retrieves marketplace data about the given item"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_item_orders(
	request: faRequest, user: TokenBearer,
	itemHash: Annotated[str, Path(title="The item to look up")],
):
	books_brief = await Request.send_template(
		user,
		"cln_books_brief",
		market_name = itemHash
	)
	if "response" in books_brief:
		books_brief = books_brief["response"]
	else:
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "An unexpected error occurred")

	ret_data = {}
	ret_data["buy_orders"] = books_brief["depth"]["BUY"]
	ret_data["sell_orders"] = books_brief["depth"]["SELL"]
	ret_data["buy_prices"] = [{"price":i[0]/10000,"amount":i[1]} for i in books_brief["BUY"]]
	ret_data["sell_prices"] = [{"price":i[0]/10000,"amount":i[1]} for i in books_brief["SELL"]]
	return ret_data

@router.get(
	"/{itemHash}/view",
	summary="Views the item ingame"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def view_item(
	request: faRequest, user: TokenBearer,
	itemHash: Annotated[str, Path(title="The item's hash to view")],
) -> bool:
	hashData = await Request.send_template(
		user,
		"cln_market_get_asset_class",
		name = itemHash
	)
	if "response" not in hashData or "asset_class" not in hashData["response"]:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
	hashData = hashData["response"]["asset_class"]
	if len(hashData) <= 0:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
	resp = await Request.send_template(
		user,
		"market_view_item1",
		params = {
			"appId": "1067",
			"assetClass": [
				{
					"name": hashData[0]["name"],
					"value": hashData[0]["value"]
				}
			]
		}
	)
	await Request.send_template(
		user,
		"market_view_item2"
	)
	return resp.get("status") == "ok"

@router.get(
	"/{itemHash}",
	summary="Gets metadata about the given item"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_item(
	request: faRequest, user: TokenBearer,
	itemHash: Annotated[str, Path(title="The item to look up")],
):
	hashData = await Request.send_template(
		user,
		"cln_market_get_asset_class",
		name = itemHash
	)
	if "response" not in hashData or "asset_class" not in hashData["response"]:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
	hashData = hashData["response"]["asset_class"]
	if len(hashData) <= 0:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
	resp = await Request.send_template(
		user,
		"GetAssetClassInfo",
		class_name0 = hashData[0]["name"],
		class_value0 = hashData[0]["value"]
	)
	if "result" not in resp or "asset" not in resp["result"]:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Item data could not be obtained")
	resp = resp["result"]["asset"]
	ret_data = {}

	ret_data["description"] = resp["descriptions"][0]["value"]
	ret_data["tags"] = resp["tags"]
	ret_data["sellable"] = bool(resp["marketable"])
	ret_data["hash"] = resp["market_hash_name"]
	ret_data["market_name"] = resp["market_name"]
	ret_data["display_name"] = resp["name"]
	ret_data["images"] = {
		"icon": resp["icon_url"],
		"image": resp["icon_url_large"]
	}
	ret_data["type"] = resp["type"]

	return ret_data

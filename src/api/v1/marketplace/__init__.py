from decimal import Decimal
from os import getenv

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi import Request as faRequest
from typing_extensions import Annotated

from api.shared import limiter
from api.v1.models import GenericEmptyResponse
from api.v1.shared import ServerBearer, TokenBearer
from utils.connection import Request

from .backend import User
from .models import Models

router = APIRouter(
	prefix = "/market",
	tags = ["marketplace"],
	responses = {status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.post(
	"/orders/{orderId}/cancel",
	summary = "Cancels an order",
	response_model=GenericEmptyResponse
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def cancel_order(
	request: faRequest, user: TokenBearer,
	orderId: Annotated[int, Path(description = "The order ID")]
):
	orders = await User(user).orders()
	if orderId not in orders:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Order ID not found")

	result = await orders[orderId].cancel()
	return {"success": result}

@router.get(
	"/orders/{orderId}",
	summary = "Gets information about an order",
	response_model=Models.OrderModel
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_order(
	request: faRequest, user: TokenBearer,
	orderId: Annotated[int, Path(description = "The order ID")]
):
	orders = await User(user).orders()
	if orderId not in orders:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Order ID not found")
	return await orders[orderId].to_json()

@router.get(
	"/orders",
	summary = "Gets the currently active orders",
	responses = {
		status.HTTP_200_OK: {"model": list[Models.OrderModel]}
	},
	response_model=list[Models.OrderModel]
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_orders(
	request: faRequest, user: TokenBearer,
	orderType: Annotated[User.Order.Type | None, Query()] = None
):
	return [await order.to_json() for order in (await User(user).orders(orderType)).values()]

@router.get(
	"/inventory",
	summary = "Gets the account's inventory contents",
	response_model=list[Models.InventoryItemModel]
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def getInventory(
	request: faRequest, user: TokenBearer
):
	inv = await User(user).inventory()
	return [
		await i.to_json()
		for i in inv.values()
	]

@router.get(
	"/balance",
	summary = "Gets the account's balance",
	response_model=Models.BalanceModel
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_balance(
	request: faRequest, user: TokenBearer
):
	return {"balance": await User(user).balance()}

@router.get(
	"/search",
	summary = "Searches the marketplace for a given item",
	responses = {
		status.HTTP_200_OK: {"model": list[Models.ItemModel]}
	},
	response_model=list[Models.ItemModel]
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def searchItem(
	request: faRequest, user: ServerBearer,
	name: Annotated[str, Query(title = "The item to search for. Leave empty to search for ALL units")] = "",
	count: Annotated[int, Query(title = "Amount to get at once")] = 25,
	page: Annotated[int, Query(title = "Pagination page. Works based off of `count`")] = 0,
):
	data = await User(user).MarketItem.search(user, name, count, page)
	return [await i.to_json() for i in data.values()]

@router.get(
	"/{itemHash}/history",
	summary = "Retrieves marketplace history data about the given item",
	response_model=Models.OrderHistoryModel
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_item_history(
	request: faRequest, user: ServerBearer,
	itemHash: Annotated[str, Path(title = "The item to look up")],
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
	summary = "Retrieves marketplace data about the given item",
	response_model=Models.OrdersModel
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_item_orders(
	request: faRequest, user: ServerBearer,
	itemHash: Annotated[str, Path(title = "The item to look up")],
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
	summary = "Views the item ingame",
	response_model=GenericEmptyResponse
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def view_item(
	request: faRequest, user: TokenBearer,
	itemHash: Annotated[str, Path(title = "The item's hash to view")],
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
	return {"success": resp.get("status") == "ok"}

@router.post(
	"/{itemHash}/sell",
	summary = "Puts up a sell order for the given `itemHash`",
	responses = {
		status.HTTP_200_OK: {"description": "Sell order has successfully been placed", "model": list[Models.SellModel]},
		status.HTTP_400_BAD_REQUEST: {"description": "Count is too high"},
		status.HTTP_404_NOT_FOUND: {"description": "Item could not be found in the inventory"}
	},
	response_model=list[Models.SellModel]
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def sell_item(
	request: faRequest, user: TokenBearer,
	itemHash: Annotated[str, Path(description = "The item's hash value")],
	price: Annotated[Decimal, Query(description = "The price in GJN to sell for (Includes gaijin's fee, not the value you get)", ge = 0.1, le = 2000, decimal_places=2)],
	count: Annotated[int, Query(description = "The amount to sell at once", gt = 0)] = 1,
	anonymous: Annotated[bool, Query(description = "Appear as an anonymous seller")] = False
):
	inventoryItems = await User(user).inventory()
	if itemHash not in inventoryItems:
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found in inventory")
	return await inventoryItems[itemHash].sell(price = int(price*100)/100, count = count, anonymous = anonymous)

@router.post(
	"/{itemHash}/buy",
	summary = "Puts up a buy order for the given `itemHash`",
	responses = {
		status.HTTP_200_OK: {"description": "The buy order has successfully been placed", "model": GenericEmptyResponse},
		status.HTTP_400_BAD_REQUEST: {"description": "Something prevented the buy order from being placed"},
		status.HTTP_403_FORBIDDEN: {"description": "Not enough funds"},
		status.HTTP_404_NOT_FOUND: {"description": "The given item doesn't exist"}
	},
	response_model=GenericEmptyResponse
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def buy_item(
	request: faRequest, user: TokenBearer,
	itemHash: Annotated[str, Path(description = "The item's hash value")],
	price: Annotated[Decimal, Query(description = "The price in GJN to buy for", ge = 0.1, le = 2000, decimal_places=2)],
	count: Annotated[int, Query(description = "The amount to buy", gt = 0)] = 1,
	anonymous: Annotated[bool, Query(description = "Appear as an anonymous buyer")] = False
):
	return await User(user).buy(item_hash = itemHash, price = float(price), count = count, anonymous = anonymous)

@router.get(
	"/{itemHash}",
	summary = "Gets metadata about the given item",
	response_model=Models.ItemModel
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_item(
	request: faRequest, user: ServerBearer,
	itemHash: Annotated[str, Path(title = "The item to look up")],
):
	item = await User.MarketItem.get(user, itemHash)
	if item is not None:
		return await item.to_json()
	raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")

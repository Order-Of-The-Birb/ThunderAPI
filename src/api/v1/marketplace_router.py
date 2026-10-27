from os import getenv
from typing_extensions import Annotated
from random import randint
from datetime import datetime, UTC
from fastapi import APIRouter, Query, Path, Request as faRequest, HTTPException, status

from utils.connection import Request
from utils.helper import dtToTimestampMs
from api.shared import limiter
from api.v1.backends.shared import ServerBearer, OptionalAuth, TokenBearer
from api.v1.backends.marketplace import Order, InventoryItem, Item
from api.v1.models.marketplace import Models
from api.v1.models.base import GenericEmptyResponse

router = APIRouter(
	prefix="/market",
	tags=["marketplace"],
	responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)

@router.post(
	"/orders/{orderId}/cancel",
	summary="Cancels an order"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def cancel_order(
	request: faRequest, user: TokenBearer,
	orderId: Annotated[int, Path(description="The order ID")]
) -> GenericEmptyResponse:
	orders = await Order.Entry.get_orders(user)
	for order in orders:
		if order.id == orderId:
			await order.cancel()
			return {"success": True}
	raise HTTPException(status.HTTP_404_NOT_FOUND, "Order ID not found")

@router.get(
	"/orders/{orderId}",
	summary="Gets information about an order"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_order(
	request: faRequest, user: TokenBearer,
	orderId: Annotated[int, Path(description="The order ID")]
):
	orders = await Order.Entry.get_orders(user)
	for order in orders:
		if order.id == orderId:
			return await order.to_json()
	raise HTTPException(status.HTTP_404_NOT_FOUND, "Order ID not found")

@router.get(
	"/orders",
	summary="Gets the currently active orders",
	responses={
		status.HTTP_200_OK: {"model": list[Models.OrderModel]}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_orders(
	request: faRequest, user: TokenBearer,
	orderType: Annotated[Order.Type | None, Query()] = None
) -> list[Models.OrderModel]:
	orders = await Order.Entry.get_orders(user)
	if orderType is None:
		return [await order.to_json() for order in orders]

	display_orders = []
	for order in orders:
		if order.type == orderType:
			display_orders.append(await order.to_json())
	return display_orders

@router.get(
	"/inventory",
	summary="Gets the account's inventory contents"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def getInventory(
	request: faRequest, user: TokenBearer
) -> list[Models.InventoryItemModel]:
	inv = await InventoryItem.get(user)
	return [await i.to_json() for i in inv]

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
		status.HTTP_200_OK: {"model": list[Models.ItemModel]}
	}
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def searchItem(
	request: faRequest, user: ServerBearer,
	name: Annotated[str, Query(title="The item to search for. Leave empty to search for ALL units")] = "",
	count: Annotated[int, Query(title="Amount to get at once")] = 25,
	page: Annotated[int, Query(title="Pagination page. Works based off of `count`")] = 0,
):
	data = await Item.search(user, name, count, page)
	return [await i.to_json() for i in data]

@router.get(
	"/{itemHash}/history",
	summary="Retrieves marketplace history data about the given item"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_item_history(
	request: faRequest, user: ServerBearer,
	itemHash: Annotated[str, Path(title="The item to look up")],
) -> Models.OrderHistoryModel:
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
	request: faRequest, user: ServerBearer,
	itemHash: Annotated[str, Path(title="The item to look up")],
) -> Models.OrdersModel:
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

@router.post(
	"/{itemHash}/sell",
	summary="Puts up a sell order for the given `itemHash`",
	responses={
		status.HTTP_200_OK: {"description": "Sell order has successfully been placed", "model": list[Models.SellModel]},
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
	inventoryItems = await InventoryItem.get(user)
	for item in inventoryItems:
		if item.hash == itemHash:
			return await item.sell(price=price, count=count, anonymous=anonymous)
	raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found in inventory")

@router.post(
	"/{itemHash}/buy",
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
	item = await Item.get(user, itemHash)
	if item:
		return await item.buy(user, price=price, count=count, anonymous=anonymous)
	raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")

@router.get(
	"/{itemHash}",
	summary="Gets metadata about the given item"
)
@limiter.shared_limit(getenv("REGULAR_RATE_LIMIT", "30/minute"), "trade")
async def get_item(
	request: faRequest, user: ServerBearer,
	itemHash: Annotated[str, Path(title="The item to look up")],
) -> Models.ItemModel:
	item = await Item.get(user, itemHash)
	if item is not None:
		return await item.to_json()
	raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")

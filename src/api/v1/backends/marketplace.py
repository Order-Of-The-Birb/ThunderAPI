import asyncio, math
from fastapi import HTTPException, status
from random import randint
from typing import Any, TypedDict
from dataclasses import dataclass, asdict, field
from enum import StrEnum
from datetime import datetime, UTC

from utils.connection import Request
from utils.auth import LoginEntry
from utils.helper import dictUtil, dtToTimestampMs
import utils.connection.network as Network
from api.v1.backends.shared import IntString

async def get_asset_class(user: LoginEntry, hash:str) -> list[dict[str, str|IntString]]:
	return await Request.send_template(
		user,
		"cln_market_get_asset_class",
		name = hash
	)
@dataclass(slots=True)
class Item:
	hash_name: str
	name: str
	commodity: bool
	icon: str
	buy_price: float
	buy_orders: int
	sell_price: float
	sell_orders: int
	tags: dict[str, str|bool]
	className: str
	classValue: str
	@classmethod
	def from_dict(cls, data:dict[str, Any]):
		tags = {}
		for tag in data["tags"]:
			tag:str
			if tag.count(":") != 1:
				... # TODO: Figure out something here
				return
			key, value = tag.split(":")
			if value == "yes":
				tags[key] = True
			elif value == "no":
				tags[key] = False
			else:
				tags[key] = value

		return cls(
			hash_name = data["hash_name"],
			name = data["name"],
			commodity = data.get("commodity", False),
			icon = data["icon"],
			buy_price = data["buy_price"] / 100000000,
			buy_orders = data["buy_depth"],
			sell_price = data["price"] / 100000000,
			sell_orders = data["depth"],
			tags = tags,
			className = data["asset_class"][0]["name"],
			classValue = data["asset_class"][0]["value"]
		)
	@classmethod
	def from_assetdata(cls, assetData:dict[str, Any], ordersData: dict[str, Any], classValues: dict[str, str]):

		return cls(
			hash_name = assetData["market_hash_name"],
			name = assetData["market_name"],
			commodity = assetData.get("commodity", False),
			icon = assetData.get("icon_url_large", assetData.get("icon_url", None)),
			buy_price = max(i[0] for i in ordersData.get("BUY", [])) / 10000,
			buy_orders = ordersData["depth"].get("BUY", 0),
			sell_price = min(i[0] for i in ordersData.get("SELL", [])) / 10000,
			sell_orders = ordersData["depth"].get("SELL", 0),
			tags = {i["category"]:i["internal_name"] for i in assetData.get("tags", [])},
			className = classValues[0]["name"],
			classValue = classValues[0]["value"]
		)

	async def to_json(self):
		data = asdict(self)

		SANITIZE = (
			dictUtil.KeyRem("className", "classValue", "LOGIN"),
		)

		return await dictUtil.run_all(data, SANITIZE)

	@staticmethod
	async def search(user: LoginEntry, name: str, count: int = 25, page: int = 0) -> tuple[Item]:
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

		items = []
		for item in data:
			items.append(Item.from_dict(item))
		return tuple(items)

	@staticmethod
	async def get(user: LoginEntry, itemHash: str) -> Item | None:
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

		resp, books_brief = await asyncio.gather(
			Request.send_template(
				user,
				"GetAssetClassInfo",
				class_name0 = hashData[0]["name"],
				class_value0 = hashData[0]["value"]
			),
			Request.send_template(
				user,
				"cln_books_brief",
				market_name = itemHash
			)
		)

		if "result" not in resp or "asset" not in resp["result"]:
			raise HTTPException(status.HTTP_404_NOT_FOUND, "Item data could not be obtained")
		resp = resp["result"]["asset"]

		if "response" in books_brief:
			books_brief = books_brief["response"]
		else:
			raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "An unexpected error occurred")

		return Item.from_assetdata(resp, books_brief, hashData)

	async def buy(self, user: LoginEntry, price: float, count: int = 1, anonymous: bool = False):
		agree_stamp = dtToTimestampMs(datetime.now(UTC))
		resp = await Request.send_template(
			user,
			"cln_market_buy",
			transactid = randint(10**6, 10**15),
			reqstamp = dtToTimestampMs(datetime.now(UTC)),
			market_name = self.hash_name,
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

#region Inventory
@dataclass(slots=True)
class InventoryItem:
	class SellData(TypedDict):
		item: str
		success: bool
		price: float
		seller_gets: float

	LOGIN: LoginEntry
	commodity:bool
	description: str
	icon_url: str
	icon_url_large: str
	hash: str
	name: str
	display_name:str
	tags: list[dict[str, str|int]]
	type: str
	marketable: bool
	name_color: str
	class_name: str
	class_value: int
	ids:list[int]
	contextid: int
	@classmethod
	def from_json(cls, data:dict[str, Any], user: LoginEntry, itemData: dict[str, Any], context: int):
		pass
		assetData: dict[str, Any] = data["result"]["asset"]
		classData: dict[str, Any] = itemData["class"][0]

		return cls(
			LOGIN=user,
			commodity=assetData.get("commodity"),
			description=assetData["descriptions"][0]["value"],
			icon_url=assetData.get("icon_url"),
			icon_url_large=assetData.get("icon_url_large"),
			hash=assetData.get("market_hash_name"),
			name=assetData.get("market_name"),
			display_name=assetData.get("name"),
			tags=assetData.get("tags", []),
			marketable=assetData.get("marketable", False),
			type=assetData.get("type", None),
			name_color=assetData.get("name_color"),
			class_name=classData["name"],
			class_value=classData["value"],
			ids=[int(itemData["id"]),],
			contextid=context
		)

	async def sell(self, price: float, count: int, anonymous: bool = False) -> tuple[SellData]:
		agree_stamp = dtToTimestampMs(datetime.now(UTC))

		gaijin_fee = price*0.15
		seller_should_get = int((price-gaijin_fee)*10000//100*100)

		soldItems = []
		sold = 0
		if len(self.ids) < count:
			raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requested selling {count} items, but user only has {len(self.ids)} items in their inventory")

		for id in list(self.ids):
			resp = await Request.send_template(
				self.LOGIN,
				"cln_market_sell",
				transactid = randint(10**6, 10**15),
				reqstamp = dtToTimestampMs(datetime.now(UTC)),
				assetid = id,
				amount = 1,
				price = int(price*10000),
				seller_should_get = seller_should_get,
				agree_stamp = agree_stamp,
				privateMode = anonymous,
				contextid = self.contextid
			)
			self.ids.remove(id)
			if resp.get("status", False):
				soldItems.append({
					"item": str(id),
					"success": "response" in resp and resp["response"].get("success", False),
					"price": price,
					"seller_gets": seller_should_get
				})
				sold += 1

			if sold >= count:
				break

		return tuple(soldItems)

	async def to_json(self):
		SANITIZE = (
			dictUtil.KeyRem("ids", "class_name", "class_value", "contextid", "LOGIN"),
			dictUtil.KeyMod("ids", convert=lambda x: [str(i) for i in x])
		)
		return await dictUtil.run_all(asdict(self), SANITIZE)

	@staticmethod
	async def get(user: LoginEntry) -> tuple[InventoryItem]:
		items:list[InventoryItem] = []
		async with Network.operation() as session:
			contexts = await Request.send_template(
				user,
				"GetContexts",
				session=session
			)
			if "result" not in contexts or not contexts["result"].get("success", False):
				raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not get contexts")
			for context in contexts["result"]["contexts"]:
				ctx_data = await Request.send_template(
					user,
					"GetContextContents",
					session=session,
					contextid = context["id"]
				)
				if "result" not in ctx_data:
					continue
				for item in ctx_data["result"]["assets"]:
					item_data = await Request.send_template(
						user,
						"GetAssetClassInfo",
						session=session,
							class_name0 = item["class"][0]["name"],
							class_value0 = item["class"][0]["value"]
					)
					if "result" not in item_data:
						continue
					for invitem in items:
						if invitem.class_name == item["class"][0]["name"] and invitem.class_value == item["class"][0]["value"]:
							invitem.ids.append(int(item["id"]))
							break
					else:
						items.append(InventoryItem.from_json(item_data, user, item, int(context["id"])))
		return tuple(items)

	@staticmethod
	async def balance(user: LoginEntry) -> float:
		data = await Request.send_template(
			user,
			"GetBalance"
		)
		if data.get("status") == "OK":
			return data["balance"]/10000
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get balance")
#endregion

class Order:
	class Type(StrEnum):
		BUY = "buy"
		SELL = "sell"
	@dataclass(frozen=True, slots=True)
	class Entry:
		LOGIN: LoginEntry
		market_hash: str
		id: IntString
		type: Order.Type
		pairId: IntString
		price: float
		timestamp: datetime
		amount: int = field(default=1)

		@classmethod
		def from_dict(cls, obj: dict[str, Any], login: LoginEntry):
			return cls(
				LOGIN=login,
				market_hash=obj["market"],
				id=int(obj["id"]),
				type=Order.Type[obj["type"]],
				pairId=int(obj["pairId"]),
				price=int(obj["localPrice"])/10000,
				timestamp=datetime.fromtimestamp(obj["time"], UTC),
				amount=int(obj["amount"])
			)

		@staticmethod
		async def get_orders(login: LoginEntry) -> tuple[Order.Entry]:
			data = await Request.send_template(login, "cln_get_user_open_orders")
			if (not data.get("success", False)) or "response" not in data:
				raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not get user's orders")

			orders = []
			for entry in data["response"]:
				orders.append(Order.Entry.from_dict(entry, login))
			return tuple(orders)

		async def cancel(self) -> bool:
			data = await Request.send_template(
				self.LOGIN,
				"cancel_order",
				transactid=1,
				reqstamp=int(datetime.now(UTC).timestamp()),
				pairId=self.pairId,
				orderId=self.id
			)
			if "response" in data:
				return data["response"].get("success", False)
			raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "An error occurred while trying to cancel this order.")

		async def to_json(self):
			SANITIZE = (
				dictUtil.KeyRem("LOGIN", "pairId"),
				dictUtil.KeyMod("id", convert=lambda x: str(x)),
			)
			return await dictUtil.run_all(asdict(self), SANITIZE)

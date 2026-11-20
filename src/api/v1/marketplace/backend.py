import asyncio
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from decimal import Decimal
from random import randint
from typing import Any, TypedDict

from fastapi import HTTPException, status

import utils.connection.network as Network
from api.v1.shared import IntString
from utils.auth import LoginEntry
from utils.connection import Request
from utils.helper import dictUtil, dtToTimestampMs


class User:
	login: LoginEntry
	def __init__(self, login: LoginEntry):
		self.login = login

	@dataclass(frozen = True, slots = True)
	class Order:
		class Type(StrEnum):
			BUY = "buy"
			SELL = "sell"
		LOGIN: LoginEntry
		market_hash: str
		id: int
		type: Type
		pairId: int
		price: float
		timestamp: datetime
		amount: int = field(default = 1)

		@classmethod
		def from_dict(cls, obj: dict[str, Any], login: LoginEntry):
			return cls(
				LOGIN = login,
				market_hash = obj["market"],
				id = int(obj["id"]),
				type = cls.Type[obj["type"]],
				pairId = int(obj["pairId"]),
				price = int(obj["localPrice"])/10000,
				timestamp = datetime.fromtimestamp(obj["time"], UTC),
				amount = int(obj["amount"])
			)

		async def cancel(self) -> bool:
			data = await Request.send_template(
				self.LOGIN,
				"cancel_order",
				transactid = 1,
				reqstamp = int(datetime.now(UTC).timestamp()),
				pairId = self.pairId,
				orderId = self.id
			)
			if "response" in data:
				return data["response"].get("success", False)
			raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "An error occurred while trying to cancel this order.")

		async def to_json(self):
			SANITIZE = (
				dictUtil.KeyRem("LOGIN", "pairId"),
				dictUtil.KeyMod("id", convert = lambda x: str(x)),
			)
			return await dictUtil.run_all(asdict(self), SANITIZE)

	@dataclass(slots = True)
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
			assetData: dict[str, Any] = data["result"]["asset"]
			classData: dict[str, Any] = itemData["class"][0]

			return cls(
				LOGIN = user,
				commodity = assetData.get("commodity"),
				description = assetData["descriptions"][0]["value"],
				icon_url = assetData.get("icon_url"),
				icon_url_large = assetData.get("icon_url_large"),
				hash = assetData.get("market_hash_name"),
				name = assetData.get("market_name"),
				display_name = assetData.get("name"),
				tags = assetData.get("tags", []),
				marketable = assetData.get("marketable", False),
				type = assetData.get("type", None),
				name_color = assetData.get("name_color"),
				class_name = classData["name"],
				class_value = classData["value"],
				ids = [int(itemData["id"]),],
				contextid = context
			)

		async def sell(self, price: Decimal | float, count: int, anonymous: bool = False) -> tuple[SellData]:
			agree_stamp = dtToTimestampMs(datetime.now(UTC))
			if isinstance(price, Decimal):
				price = int(price*100)/100

			price = int(round(price*10000, -2))
			seller_should_get = int(round(price*0.85, -2))

			soldItems = []
			sold = 0
			if len(self.ids) < count:
				raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Requested selling {count} items, but user only has {len(self.ids)} items in their inventory")

			for id in list(self.ids)[:count]:
				resp = await Request.send_template(
					self.LOGIN,
					"cln_market_sell",
					transactid = randint(10**6, 10**15),
					reqstamp = dtToTimestampMs(datetime.now(UTC)),
					assetid = id,
					amount = 1,
					price = price,
					seller_should_get = seller_should_get,
					agree_stamp = agree_stamp,
					privateMode = anonymous,
					contextid = self.contextid
				)
				success = resp.get("response", {}).get("success", False)
				if success:
					self.ids.remove(id)
					sold += 1
				soldItems.append({
					"item": str(id),
					"success": success,
					"price": price/10000,
					"seller_gets": seller_should_get/10000
				})

			return tuple(soldItems)

		async def to_json(self):
			SANITIZE = (
				dictUtil.KeyRem("class_name", "class_value", "contextid", "LOGIN"),
				dictUtil.KeyMod("ids", new_name="count", convert=lambda x: len(x))
			)
			return await dictUtil.run_all(asdict(self), SANITIZE)

	@dataclass(slots = True)
	class MarketItem:
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
					raise RuntimeError(f"Somehow item {data["hash_name"]}'s tag '{tag}' has more than 1 separator")
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
				buy_price = max((i[0] for i in ordersData.get("BUY", [])), default = 0) / 10000,
				buy_orders = ordersData["depth"].get("BUY", 0),
				sell_price = min((i[0] for i in ordersData.get("SELL", [])), default = 0) / 10000,
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
		async def search(user: LoginEntry, name: str, count: int = 25, page: int = 0) -> dict[str, User.MarketItem]:
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

			items = {}
			for item in data:
				items[item["hash_name"]] = User.MarketItem.from_dict(item)
			return items

		@staticmethod
		async def get(user: LoginEntry, itemHash: str) -> User.MarketItem:
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

			return User.MarketItem.from_assetdata(resp, books_brief, hashData)

	async def orders(self, orderType: Order.Type | None = None) -> dict[int, "Order"]:
		data = await Request.send_template(self.login, "cln_get_user_open_orders")
		if (not data.get("success", False)) or "response" not in data:
			raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not get user's orders")

		orders = {}
		for entry in data["response"]:
			if orderType is None or orderType == self.Order.Type[entry["type"]]:
				orders[int(entry["id"])] = User.Order.from_dict(entry, self.login)
		return orders

	async def balance(self) -> float:
		data = await Request.send_template(
			self.login,
			"GetBalance"
		)
		if data.get("status") == "OK":
			return data["balance"]/10000
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get balance")

	async def inventory(self) -> dict[tuple[str, Any, int], InventoryItem]:
		items:dict[tuple[str, Any, int], User.InventoryItem] = {}
		async with Network.operation() as session:
			contexts = await Request.send_template(
				self.login,
				"GetContexts",
				session = session
			)
			if "result" not in contexts or not contexts["result"].get("success", False):
				raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not get contexts")
			for context in contexts["result"]["contexts"]:
				ctx_data = await Request.send_template(
					self.login,
					"GetContextContents",
					session = session,
					contextid = context["id"]
				)
				if "result" not in ctx_data:
					continue
				for item in ctx_data["result"]["assets"]:
					item_data = await Request.send_template(
						self.login,
						"GetAssetClassInfo",
						session = session,
							class_name0 = item["class"][0]["name"],
							class_value0 = item["class"][0]["value"]
					)
					if "result" not in item_data:
						continue
					key = (item["class"][0]["name"], item["class"][0]["value"], int(context["id"]))
					if key in items:
						items[key].ids.append(int(item["id"]))
					else:
						items[key] = self.InventoryItem.from_json(item_data, self.login, item, int(context["id"]))
		return items

	async def sell(self, item_hash: str, price: Decimal | float, count: int = 1, anonymous: bool = False) -> tuple[InventoryItem.SellData, ...]:
		matching = [item for item in (await self.inventory()).values() if item.hash == item_hash]
		if not matching:
			raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found in inventory")

		total = sum(len(item.ids) for item in matching)
		if total < count:
			raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Requested selling {count} items, but user only has {total} items in their inventory")

		sold = []
		remaining = count
		for item in matching:
			if remaining <= 0:
				break
			take = min(len(item.ids), remaining)
			sold.extend(await item.sell(price = price, count = take, anonymous = anonymous))
			remaining -= take

		return tuple(sold)

	async def buy(self, item_hash: str, price: float, count: int = 1, anonymous: bool = False):
		agree_stamp = dtToTimestampMs(datetime.now(UTC))
		resp = await Request.send_template(
			self.login,
			"cln_market_buy",
			transactid = randint(10**6, 10**15),
			reqstamp = dtToTimestampMs(datetime.now(UTC)),
			market_name = item_hash,
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

	async def get_asset_class(self, hash:str) -> list[dict[str, str|IntString]]:
		return await Request.send_template(
			self.login,
			"cln_market_get_asset_class",
			name = hash
		)

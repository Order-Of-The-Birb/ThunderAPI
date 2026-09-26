from fastapi import HTTPException, status
from typing import Any
from dataclasses import dataclass, asdict

from tools import Request
from utils.auth import UserAuth
from utils import networkManager
from api.v1.shared import IntString

async def get_asset_class(user: UserAuth.Entry, hash:str) -> list[dict[str, str|IntString]]:
	return await Request.send_template(
		user,
		"cln_market_get_asset_class",
		name = hash
	)

#region Inventory
@dataclass(slots=True)
class InventoryItem:
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
	_class_name: str
	_class_value: int
	ids:list[int]
	contextid: str
	@classmethod
	def from_json(cls, data:dict[str, Any], classdata:dict[str, str|int], id:int, context:str):
		cname = classdata["name"]
		cval = classdata["value"]
		return cls(
			commodity=data.get("commodity"),
			description=data["descriptions"][0]["value"],
			icon_url=data.get("icon_url"),
			icon_url_large=data.get("icon_url_large"),
			hash=data.get("market_hash_name"),
			name=data.get("market_name"),
			display_name=data.get("name"),
			tags=data.get("tags", []),
			marketable=data.get("marketable", False),
			type=data.get("type", ""),
			name_color=data.get("name_color"),
			_class_name=cname,
			_class_value=cval,
			ids=[id,],
			contextid=context
		)
	def to_json(self):
		return asdict(self)
async def get_inventory(user: UserAuth.Entry) -> list[InventoryItem]:
	items:list[InventoryItem] = []
	async with networkManager.operation() as session:
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
					if invitem._class_name == item["class"][0]["name"] and invitem._class_value == item["class"][0]["value"]:
						invitem.ids.append(int(item["id"]))
						break
				else:
					items.append(InventoryItem.from_json(item_data["result"]["asset"], item["class"][0], int(item["id"]), context["id"]))
	return items

async def item_in_inventory(user: UserAuth.Entry, item_hash:str) -> InventoryItem|None:
	inventory = await get_inventory(user)
	for item in inventory:
		if item.hash == item_hash:
			return item
	return None
#endregion
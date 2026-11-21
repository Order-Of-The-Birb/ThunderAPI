import pytest
from fastapi import HTTPException, status

from src.utils import auth

from .. import templates
from ..helpers import response_provider, run_tests

group = templates.Groups.LOGIN

async def test_login_success():
	await run_tests("", "", tests = group.SUCCESS, func = auth.login)

async def test_login_failures():
	await run_tests("", "", tests = group.FAILURE, func = auth.login)

async def test_2fa_success():
	templ = templates.load(group.TWO_FACTOR)

	async def provider(state: str = "init"):
		states = {
			"await_2fa": "accept",
			"2fa_login": "success",
		}
		if state in states:
			return templ[states[state]]
		return templ[state]

	async with response_provider(provider):
		with pytest.raises(HTTPException) as exc_info:
			await auth.login("", "")
		assert exc_info.value.status_code == status.HTTP_206_PARTIAL_CONTENT

		entry = auth._PENDING_2FA[""]
		await entry.await_task
		assert await auth.login("", "") == templ["success"]
		assert "" not in auth._PENDING_2FA

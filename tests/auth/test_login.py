import pytest
from fastapi import HTTPException
from . import templates
from typing import NamedTuple, Any, Iterable
from collections.abc import Awaitable, Callable

from src.utils.auth import ServerAuth, UserAuth, login, _PENDING_2FA

group = templates.Groups.LOGIN

async def test_login_success():
	await run_tests("", "", tests=group.SUCCESS, func=login)

async def test_login_failures():
	await run_tests("", "", tests=group.FAILURE, func=login)

async def test_2fa_success():
	await run_tests("", "", tests=group.TWO_FACTOR, func=login, extra_templates={"2fa_login": "success"})

async def run_tests(*args, tests: Iterable[templates._Group] | templates._Group, func: Callable[[str], Awaitable[dict[str, Any]]], extra_templates: dict[str, str] | None = None, **kwargs):
	if extra_templates is None:
		extra_templates = {}
	if isinstance(tests, templates._Group):
		tests = (tests,)
	async def provider(state: str = "init"):
		nonlocal test
		templ = templates.load(test)
		if state in templ:
			return templ[state]
		if state in extra_templates:
			return extra_templates[state]
		raise FileNotFoundError(f"State `{state}` not found in template '{templ}'")
	for test in tests:
		expected = test.value[1]
		if expected is not None:
			with pytest.raises(type(expected), check=lambda x: type(x) == type(expected)) as exc_info:
				await func(*args, **kwargs, response_provider=provider)
			if type(expected) is HTTPException:
				assert exc_info.value.status_code == expected.status_code
		else:
			await func(*args, **kwargs, response_provider=provider)

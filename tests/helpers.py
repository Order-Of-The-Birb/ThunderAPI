from collections.abc import Awaitable, Callable
from typing import Any, Iterable

import pytest
from fastapi import HTTPException
from typing_extensions import Annotated, Doc
from utils.connection import network
from contextlib import asynccontextmanager

from . import templates

@asynccontextmanager
async def response_provider(provider):
	network._RESP_PROVIDER = provider
	try:
		yield
	finally:
		network._RESP_PROVIDER = None

async def run_tests(
	*args,
	tests: Iterable[templates._Group] | templates._Group,
	func: Callable[..., Awaitable[dict[str, Any]]],
	extra_templates: Annotated[dict[str, str] | None, Doc("`Key-Value` pair of `State-Template`")] = None,
	**kwargs
):
	if extra_templates is None:
		extra_templates = {}
	if isinstance(tests, templates._Group):
		tests = (tests,)
	for test in tests:
		async def provider(state: str = "init", *, test=test):
			templ = templates.load(test)
			if state in templ:
				return templ[state]
			if state in extra_templates:
				if extra_templates[state] not in templ:
					raise FileNotFoundError(f"State `{extra_templates[state]}` not found in template '{templ}'")
				return templ[extra_templates[state]]
			raise FileNotFoundError(f"State `{state}` not found in template '{templ}'")
		async with response_provider(provider):
			expected = test.value[1]
			if expected is not None:
				with pytest.raises(type(expected), check = lambda x, expected = expected: type(x) is type(expected)) as exc_info:
					await func(*args, **kwargs)
				if type(expected) is HTTPException:
					assert exc_info.value.status_code == expected.status_code
			else:
				await func(*args, **kwargs)

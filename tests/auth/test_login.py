from src.utils import auth

from .. import templates
from ..helpers import run_tests

group = templates.Groups.LOGIN

async def test_login_success():
	await run_tests("", "", tests = group.SUCCESS, func = auth.login)

async def test_login_failures():
	await run_tests("", "", tests = group.FAILURE, func = auth.login)

async def test_2fa_success():
	await run_tests("", "", tests = group.TWO_FACTOR, func = auth.login, extra_templates = {"2fa_login": "success"})

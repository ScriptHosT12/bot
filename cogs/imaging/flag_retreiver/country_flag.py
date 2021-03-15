import typing

import aiohttp

import difflib

from .abc import FlagRetriever


class CountryFlagRetriever(FlagRetriever):
    @property
    def schema(self):
        return "country"

    def __init__(self):
        self._codes = None
        self._codes_inverted = None

    async def get_codes(self) -> dict:
        if self._codes is None:
            async with aiohttp.request("GET", f"https://flagcdn.com/en/codes.json") as code_response:
                self._codes = await code_response.json()
                self._codes = {k.lower(): v for k, v in self._codes.items()}

        return self._codes

    async def code_from_name(self, name) -> str:
        if self._codes_inverted is None:
            codes = await self.get_codes()
            self._codes_inverted = {v: k for k, v in codes.items()}

        return self._codes_inverted[name]

    # noinspection PyTypeChecker
    async def url_from_name(self, name) -> typing.Optional[typing.Tuple[str, str]]:
        name = name.lower()
        codes = await self.get_codes()
        if name in codes:
            return f"https://flagcdn.com/w320/{name}.png", codes[name]
        else:
            match = difflib.get_close_matches(name, codes.values(), 1, 0.8)
            if match:
                code = await self.code_from_name(match[0])
                return f"https://flagcdn.com/w320/{code}.png", match[0]

    def __str__(self):
        return "flagcdn"

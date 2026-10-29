from typing import Self

import httpx
from scrapers.models.lok_sabha import MemberDetailData, MemberListResponse


class DigitalSansad:
    def __init__(self):
        self._base_url = "https://sansad.in/api_ls"
        self._client = None

    async def __aenter__(self) -> Self:
        if not self._client:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_lok_sabha_members(self) -> MemberListResponse:
        if not self._client:
            raise RuntimeError("Httpx client not initialized")

        result = await self._client.get(
            "/member",
            params={"size": 12000},
        )
        result.raise_for_status()
        members = MemberListResponse.model_validate_json(result.content)
        return members

    async def get_lok_sabha_member_details(self, mpsNo: int):
        if not self._client:
            raise RuntimeError("Httpx client not initialized")

        result = await self._client.get(f"/member/{mpsNo}", params={"locale": "en"})
        result.raise_for_status()
        member_detail = MemberDetailData.model_validate_json(result.content)
        return member_detail

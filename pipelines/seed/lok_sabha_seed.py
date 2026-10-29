import asyncio
from pathlib import Path

from scrapers.digital_sansad import DigitalSansad
from settings import get_settings
from storage.r2_client import R2Storage


class LokSabhaSeed:
    def __init__(self) -> None:
        self._digital_sansad_scraper = DigitalSansad()
        self._r2_client = R2Storage()
        settings = get_settings()
        self._data_path = Path(__file__).parent.parent / settings.data_folder
        self._data_path.mkdir(parents=True, exist_ok=True)
        self._all_members_file = settings.all_members_file_key

    def save_all_members(self, all_members):
        file_path = self._data_path / f"{self._all_members_file}.json"
        file_path.write_text(all_members, encoding="utf-8")
        return file_path

    async def upsert_member_list(self):
        async with self._digital_sansad_scraper:
            all_members = await self._digital_sansad_scraper.get_lok_sabha_members()
            # Upsert this to an r2 file, use consistent key, this will not be an actively running step
            # Since this data rarely changes, we will be using this one to fill all basic details
            # about all members
            file_path = await asyncio.to_thread(
                self.save_all_members, all_members.model_dump_json(indent=2)
            )
            await asyncio.to_thread(
                self._r2_client.upload_file,
                file_path=str(file_path),
                file_id=f"{self._all_members_file}.json",
                content_type="application/json",
            )

            # Then loop over the individual responses with error handling

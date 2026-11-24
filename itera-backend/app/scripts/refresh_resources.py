"""Re-fetch learning resources for every saved roadmap with the current selection rules.

Run inside the API container:  python -m app.scripts.refresh_resources
"""
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.generated_roadmap import GeneratedRoadmap
from app.services.roadmap_service import refresh_roadmap_resources


async def main() -> None:
    async with AsyncSessionLocal() as db:
        roadmaps = (await db.execute(select(GeneratedRoadmap))).scalars().all()
        for rm in roadmaps:
            topics = await refresh_roadmap_resources(db, rm)
            await db.commit()
            print(f"Refreshed {topics} topics in '{rm.title}' ({rm.id})")
        print(f"Done: {len(roadmaps)} roadmaps")


if __name__ == "__main__":
    asyncio.run(main())

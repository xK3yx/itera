"""Re-fetch learning resources in saved roadmaps with the current selection rules.

Run inside the API container:  python -m app.scripts.refresh_resources

Each topic costs about 215 YouTube quota units (the free daily quota is 10,000), so a
large database may take several days. The script stops cleanly when the quota runs
out; run it again the next day and it continues with the topics not yet refreshed.
"""
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.generated_roadmap import GeneratedRoadmap
from app.services.roadmap_service import refresh_roadmap_resources


async def main() -> None:
    async with AsyncSessionLocal() as db:
        roadmaps = (await db.execute(select(GeneratedRoadmap).order_by(GeneratedRoadmap.created_at.desc()))).scalars().all()
        total = 0
        for rm in roadmaps:
            updated, finished = await refresh_roadmap_resources(db, rm)
            await db.commit()
            total += updated
            print(f"{'Done' if finished else 'Partly done'}: {updated} topics in '{rm.title}' ({rm.id})")
            if not finished:
                print("Stopped: a YouTube lookup failed, most likely the daily quota. Run again tomorrow to continue.")
                break
        print(f"Refreshed {total} topics.")


if __name__ == "__main__":
    asyncio.run(main())

"""CLI entrypoint for seeding the database.

Usage:
    uv run python -m app.seeds                    # seed all scenarios
    uv run python -m app.seeds snowstorm          # just scenario 2
    uv run python -m app.seeds diversion          # just scenario 1
    uv run python -m app.seeds delay              # just scenario 3
    uv run python -m app.seeds --reset            # drop + recreate tables first
"""

import asyncio
import sys

from app.db.engine import async_session, drop_db, init_db
from app.seeds import scenario_delay, scenario_diversion, scenario_snowstorm


async def main() -> None:
    args = set(sys.argv[1:])

    if "--reset" in args:
        print("Dropping all tables...")
        await drop_db()
        args.discard("--reset")

    print("Creating tables...")
    await init_db()

    scenarios = args or {"snowstorm", "diversion", "delay"}

    async with async_session() as session:
        if "snowstorm" in scenarios:
            dis_id = await scenario_snowstorm.seed(session)
            print(f"Seeded snowstorm scenario: {dis_id} (150 passengers, 6 flights)")

        if "diversion" in scenarios:
            dis_id = await scenario_diversion.seed(session)
            print(f"Seeded diversion scenario: {dis_id} (30 passengers, 1 flight)")

        if "delay" in scenarios:
            dis_id = await scenario_delay.seed(session)
            print(f"Seeded delay scenario: {dis_id} (40 passengers, 1 flight)")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())

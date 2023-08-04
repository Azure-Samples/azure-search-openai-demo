import asyncio

from app import create_app

loop = asyncio.get_event_loop()
app = loop.run_until_complete(create_app())

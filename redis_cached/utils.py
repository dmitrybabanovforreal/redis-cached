from typing import Coroutine
import asyncio


background_tasks = set()


def fire_background_task(coro: Coroutine) -> None:
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

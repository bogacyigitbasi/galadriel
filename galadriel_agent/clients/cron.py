import asyncio

from galadriel_agent.agent import AgentInput, AgentOutput
from galadriel_agent.entities import Message, PushOnlyQueue


class Cron(AgentInput, AgentOutput):
    def __init__(self, interval_seconds: int):
        self.interval_seconds = interval_seconds

    async def start(self, queue: PushOnlyQueue):
        while True:
            try:
                await queue.put(Message(content=""))
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def send(self, request: Message, response: Message, proof: str):
        pass

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List
from typing import Optional

from dotenv import load_dotenv
from galadriel_agent.entities import Message
from galadriel_agent.entities import ShortTermMemory

from galadriel_agent.clients.client import Client
from galadriel_agent.clients.client import PushOnlyQueue
from galadriel_agent.clients.s3 import S3Client
from galadriel_agent.domain import add_conversation_history
from galadriel_agent.domain import generate_proof
from galadriel_agent.domain import publish_proof
from galadriel_agent.logging_utils import init_logging


@dataclass
class AgentConfig:
    pass


class UserAgent:

    async def run(self, request: Message) -> Message:
        raise RuntimeError("Function not implemented")


class AgentState:
    # TODO: knowledge_base: KnowledgeBase
    pass


# This is just a rough sketch on how the GaladrielAgent itself will be implemented
# This is not meant to be read or modified by the end developer
class GaladrielAgent:
    def __init__(
        # pylint:disable=R0917
        self,
        agent_config: Optional[AgentConfig],
        clients: List[Client],
        user_agent: UserAgent,
        s3_client: Optional[S3Client] = None,
        short_term_memory: Optional[ShortTermMemory] = None,
    ):
        self.agent_config = agent_config
        self.clients = clients
        self.user_agent = user_agent
        self.s3_client = s3_client
        self.short_term_memory = short_term_memory

        env_path = Path(".") / ".env"
        load_dotenv(dotenv_path=env_path)
        # AgentConfig should have some settings for debug?
        init_logging(False)

    async def run(self):
        client_input_queue = asyncio.Queue()
        push_only_queue = PushOnlyQueue(client_input_queue)
        for client in self.clients:
            asyncio.create_task(client.start(push_only_queue))

        await self.load_state(agent_state=None)
        while True:
            request = await client_input_queue.get()
            await self.run_request(request)

    async def run_request(self, request: Message):
        request = await self._add_conversation_history(request)
        response = await self.user_agent.run(request)
        if response:
            proof = await self._generate_proof(request, response)
            await self._publish_proof(request, response, proof)
            for client in self.clients:
                await client.post_output(request, response, proof)
        # await self.upload_state()

    async def _add_conversation_history(self, request: Message) -> Message:
        if self.short_term_memory:
            return add_conversation_history.execute(request, self.short_term_memory)
        return request

    async def _generate_proof(self, request: Message, response: Message) -> str:
        return generate_proof.execute(request, response)

    async def _publish_proof(self, request: Message, response: Message, proof: str):
        publish_proof.execute(request, response, proof)

    # State management functions
    async def export_state(self) -> AgentState:
        pass

    async def load_state(self, agent_state: AgentState):
        pass

    async def upload_state(self):
        state = self.export_state()
        await self.s3_client.upload_file(state)

    async def restore_state(self):
        state = await self.s3_client.download_file()
        self.load_state(state)

import asyncio
import json
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from galadriel_agent.agent import GaladrielAgent
from galadriel_agent.clients.database import DatabaseClient
from galadriel_agent.clients.llms.galadriel import GaladrielClient
from galadriel_agent.logging_utils import init_logging
from galadriel_agent.models import TwitterAgentConfig
from galadriel_agent.plugins.twitter.twitter_agent import TwitterAgent
from galadriel_agent.plugins.twitter.twitter_client import TwitterClient


def _load_dotenv():
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path=env_path)


async def main():
    agent_config = _load_agent_config()

    galadriel_client = GaladrielClient()
    database_client = DatabaseClient(None)
    twitter_client = TwitterClient(
        agent=agent_config,
        database_client=database_client,
    )

    # Set up my own agent
    twitter_agent = TwitterAgent(
        agent_config=agent_config,
        llm_client=galadriel_client,
        database_client=database_client,
    )

    galadriel_agent = GaladrielAgent(
        agent_config=agent_config,
        clients=[twitter_client],
        user_agent=twitter_agent,
    )
    await galadriel_agent.run()


def _load_agent_config():
    _load_dotenv()
    agent_name = "daige"
    agent_path = Path("agent_configurator") / f"{agent_name}.json"
    with open(agent_path, "r", encoding="utf-8") as f:
        agent_dict = json.loads(f.read())
    init_logging(agent_dict.get("settings", {}).get("debug"))
    missing_fields: List[str] = [
        field
        for field in TwitterAgentConfig.required_fields()
        if not agent_dict.get(field)
    ]
    if missing_fields:
        raise KeyError(
            f"Character file is missing required fields: {', '.join(missing_fields)}"
        )
    return TwitterAgentConfig.from_json(agent_dict)


if __name__ == "__main__":
    asyncio.run(main())

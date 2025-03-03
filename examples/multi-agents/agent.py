import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from galadriel import AgentRuntime, CodeAgent
from galadriel.clients import SimpleMessageClient
from galadriel.core_agent import LiteLLMModel, DuckDuckGoSearchTool


load_dotenv(dotenv_path=Path(".") / ".env", override=True)
model = LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

managed_web_agent = CodeAgent(
    tools=[DuckDuckGoSearchTool()],
    model=model,
    name="web_search",
    description="Runs web searches for you. Give it your query as an argument.",
)

manager_agent = CodeAgent(tools=[], model=model, managed_agents=[managed_web_agent])

# Add basic client which sends two messages to the agent and prints agent's result
client = SimpleMessageClient("What's the most recent of Daige on X (twitter)?")

# Set up the runtime
runtime = AgentRuntime(
    agent=manager_agent,
    inputs=[client],
    outputs=[client],
)

# Run the agent
asyncio.run(runtime.run())

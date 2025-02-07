import json
from pathlib import Path

from rich.text import Text

from galadriel import ToolCallingAgent
from galadriel.core_agent import LogLevel
from galadriel.domain.prompts.format_prompt import load_agent_template
from galadriel.entities import AgentMessage
from galadriel.entities import Message

DISCORD_SYSTEM_PROMPT = """
{{system}}

# Areas of Expertise
{{knowledge}}

# About {{agent_name}}:
{{bio}}
{{lore}}
{{topics}}

# Task: You received a new message on discord from {{user_name}}. You must reply in the voice and style of {{agent_name}}, here's the message:
{{message}}

Be very brief, and concise, add a statement in your voice.
Maintain a natural conversation on discord.
Don't overuse emojis.
Please remember the chat history and use it to answer the question.
"""


class ElonMuskAgent(ToolCallingAgent):
    def __init__(self, character_json_path: str, **kwargs):
        super().__init__(**kwargs)
        try:
            self.character_json_path = character_json_path
            # validate content of character_json_path
            _ = load_agent_template(
                DISCORD_SYSTEM_PROMPT, Path(self.character_json_path)
            )
        except Exception as e:
            self.logger.log(
                Text(f"Error validating character file: {e}"), level=LogLevel.ERROR
            )
            raise e

    async def execute(self, message: Message) -> Message:
        try:
            # Load the agent template on every execution to ensure randomness
            character_prompt = load_agent_template(
                DISCORD_SYSTEM_PROMPT, Path(self.character_json_path)
            )
            task_message = character_prompt.replace(
                "{{message}}", message.content
            ).replace("{{user_name}}", message.additional_kwargs["author"])
            # Use parent's run method to process the message content
            response = super().run(
                task=task_message,
                stream=False,
                reset=False,  # retain memory
            )

            # Extract message text if response is in JSON format
            response_text = str(response)
            try:
                response_json = json.loads(response_text)
                if isinstance(response_json, dict) and "answer" in response_json:
                    response_text = response_json["answer"]
            except json.JSONDecodeError:
                pass  # Not JSON format, use original response

            return AgentMessage(
                content=response_text,
                conversation_id=message.conversation_id,
            )
        except Exception as e:
            self.logger.log(
                Text(f"Error processing message: {e}"), level=LogLevel.ERROR
            )
            return None

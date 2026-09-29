import inspect
import json
import os
from dataclasses import dataclass
import gateway_pb2
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MODEL = "openai/gpt-oss-120b"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TOOL_SCHEMAS = [
    {"type": "browser_search"},
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a bash command on the user's machine. Use this when the task needs the local shell.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The bash command to run",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


TOOLS = {}

@dataclass
class ModelReply:
    text: str
    tool_calls: list
    assistant_message: object

def call_model(messages: list) -> ModelReply:
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
        reasoning_effort="low",
        # On-demand OTPM for this model is 1000. Groq reserves max_completion_tokens
        # up front, and the unset default (1222) is already over the limit.
        # 480 leaves room for a tool call and a follow-up answer in the same minute.
        max_completion_tokens=480,
    )
    message = completion.choices[0].message

    tool_calls = []
    for tool_call in message.tool_calls or []:
        tool_calls.append(
            gateway_pb2.ToolCall(
                tool_call_id=tool_call.id,
                name=tool_call.function.name,
                arguments_json=tool_call.function.arguments,
            )
        )

    return ModelReply(
        text=message.content or "",
        tool_calls=tool_calls,
        assistant_message=message,
    )

def run_tool(name:str, arguments_json: str) -> str:
    if name not in TOOLS:
        raise ValueError(f"Unknown too: {name}")

    arguments = json.loads(arguments_json or "{}")
    function = TOOLS[name]
    accepted = inspect.signature(function).parameters
    filtered = {key: value for key, value in arguments.items() if key in accepted}
    return str(function(**filtered))
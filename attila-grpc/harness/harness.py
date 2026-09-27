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
    {
        "type": "function",
        "function": {
            "name": "echo",
            "description": "Repeat the given text back.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        },
    }
]

def echo(text: str) -> str:
    return text

TOOLS = {
    "echo": echo
}

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
    return str(TOOLS[name](**arguments))
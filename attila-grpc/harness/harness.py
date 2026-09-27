import json
import os
from dataclasses import dataclass
import gateway_pb2
from groq import Groq
from dotenv import load_dotenv

# web Search Library
from ddgs import DDGS

load_dotenv()

MODEL = "openai/gpt-oss-120b"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Use this when the answer depends on facts you do not already know.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


def web_search(query: str) -> str:
    results = DDGS().text(query, max_results=5)
    if not results:
        return f"No results for {query}"

    lines = []
    for result in results:
        title = result.get("title", "")
        href = result.get("href", "")
        body = result.get("body", "")
        lines.append(f"{title}\n{href}\n{body}")
    return "\n\n".join(lines)

TOOLS = {
    "web_search": web_search
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
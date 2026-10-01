import psycopg2

import gateway_pb2
import gateway_pb2_grpc
from harness.harness import run_tool, call_model

import grpc
from concurrent import futures
import threading
import time
from dotenv import load_dotenv
import os

load_dotenv()

# One chat until RunRequest carries its own conversation id.
# Electron currently sends a new run_id for every prompt, so run_id cannot
# be used to reload earlier turns.
# Keep this a string. psycopg2 cannot adapt uuid.UUID unless an adapter is registered.
CONVERSATION_ID = "00000000-0000-0000-0000-000000000001"

class GatewayServicer(gateway_pb2_grpc.AttilaGatewayServicer):
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
        self.conn.autocommit = True
        self.db_lock = threading.Lock()

    def load_context(self, conversation_id):
        with self.db_lock, self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT sender, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at, id
                """,
                (conversation_id,),
            )
            rows = cur.fetchall()
        roles = {"client": "user", "agent": "assistant"}
        return [{"role": roles[sender], "content": content} for sender, content in rows]

    def save_message(self, conversation_id, sender, content):
        with self.db_lock, self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (conversation_id, sender, content)
                VALUES (%s, %s, %s)
                """,
                (conversation_id, sender, content),
            )

    def Health(self, request, context):
        return gateway_pb2.HealthResponse(
            status=gateway_pb2.StatusType.STATUS_ACTIVE
        )

    def SubmitTask(self, request, context):
        print("Task Request Made:")
        print(request)
        for _ in range(3):
            task_response = gateway_pb2.TaskResponse()
            task_response.request_id = request.request_id
            task_response.prompt = request.content
            task_response.response = f"{task_response.request_id} \nTask: {task_response.prompt} \nType: {request.type} \nResponse: bruh"
            yield task_response
            time.sleep(3)

    def RunAgent(self, request_iterator, context):
        print("Run Agent Request Made:")
        # request_iterator is the incoming client stream.
        # The first message is the prompt. Later messages are tool results.
        incoming = next(request_iterator)
        if not incoming.HasField("run_request"):
            yield gateway_pb2.AgentEvent(
                run_failed=gateway_pb2.RunFailed(message="first message must be run_request"),
            )
            return

        request = incoming.run_request
        # Prior turns from attiladb, then this prompt. call_model sees the whole chat.
        messages = self.load_context(CONVERSATION_ID)
        messages.append({"role": "user", "content": request.prompt})
        self.save_message(CONVERSATION_ID, "client", request.prompt)

        for step in range(1, 10):
            yield gateway_pb2.AgentEvent(
                run_id=request.run_id,
                model_started=gateway_pb2.ModelStarted(
                    model_name="openai/gpt-oss-120b",
                )
            )

            # Wait for Groq to return text and tool calls if needed.
            reply = call_model(messages=messages)

            yield gateway_pb2.AgentEvent(
                run_id=request.run_id,
                model_finished=gateway_pb2.ModelFinished(
                    text=reply.text,
                    tool_calls=reply.tool_calls,
                )
            )

            if not reply.tool_calls:
                # This is the model's final answer. Save it so the next run can load it.
                self.save_message(CONVERSATION_ID, "agent", reply.text)
                yield gateway_pb2.AgentEvent(
                    run_id=request.run_id,
                    run_completed=gateway_pb2.RunCompleted(final_text=reply.text)
                )
                return

            messages.append(reply.assistant_message)

            for call in reply.tool_calls:
                yield gateway_pb2.AgentEvent(
                    run_id=request.run_id,
                    tool_started=gateway_pb2.ToolStarted(
                        tool_call_id=call.tool_call_id,
                        name=call.name,
                        arguments_json=call.arguments_json,
                    ),
                )

                if call.name == "bash":
                    # Pause the loop. Let Electron run the command and send the ToolResult back on the stream
                    result = next(request_iterator).tool_result
                    output = result.output
                    ok = result.ok
                else:
                    output = run_tool(call.name, call.arguments_json)
                    ok = True

                yield gateway_pb2.AgentEvent(
                    run_id=request.run_id,
                    tool_finished=gateway_pb2.ToolFinished(
                        tool_call_id=call.tool_call_id,
                        name=call.name,
                        output=output,
                        ok=ok,
                    ),
                )

                # Give that output back to Groq for the next model step.
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.tool_call_id,
                    "name": call.name,
                    "content": output,
                })
                
        # The model kept calling tools until the step cap. The stream ends.
        yield gateway_pb2.AgentEvent(
            run_id=request.run_id,
            run_failed=gateway_pb2.RunFailed(message="max steps"),
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    gateway_pb2_grpc.add_AttilaGatewayServicer_to_server(GatewayServicer(), server)
    server.add_insecure_port("localhost:50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
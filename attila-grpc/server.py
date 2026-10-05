import psycopg2
from psycopg2.extras import Json

import gateway_pb2
import gateway_pb2_grpc
from harness.harness import run_tool, call_model
from compaction import prepare_context

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
# We will update this later once authenticated users are tracked in PostgreSQL.
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

    # User and final-answer rows store the same dict the model will see.
    def save_message(self, conversation_id, sender, content):
        payload = (
            {"role": "user", "content": content}
            if sender == "client"
            else {"role": "assistant", "content": content}
        )
        with self.db_lock, self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (conversation_id, sender, content, message)
                VALUES (%s, %s, %s, %s)
                """,
                (conversation_id, sender, content, Json(payload)),
            )

    # Edit: one transaction for a whole tool step, so a crash cannot store
    # the assistant tool call without its results.
    def save_messages(self, conversation_id, messages):
        with self.db_lock:
            self.conn.autocommit = False
            try:
                with self.conn.cursor() as cur:
                    for message in messages:
                        cur.execute(
                            """
                            INSERT INTO messages (conversation_id, message)
                            VALUES (%s, %s)
                            """,
                            (conversation_id, Json(message)),
                        )
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
            finally:
                self.conn.autocommit = True

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
        messages, error = prepare_context(
            self.conn, self.db_lock, CONVERSATION_ID, request.prompt
        )
        if error:
            yield gateway_pb2.AgentEvent(
                run_id=request.run_id,
                run_failed=gateway_pb2.RunFailed(message=error),
            )
            return
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
            # Edit: plain dict, not the Groq SDK object. Saved only after the loop below.
            stored = [{
                "role": "assistant",
                "content": reply.text or None,
                "tool_calls": [
                    {
                        "id": call.tool_call_id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": call.arguments_json,
                        },
                    }
                    for call in reply.tool_calls
                ],
            }]

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
                # Edit: the same dict is appended to `stored` and written with the assistant message.
                tool_message = {
                    "role": "tool",
                    "tool_call_id": call.tool_call_id,
                    "name": call.name,
                    "content": output,
                }
                messages.append(tool_message)
                stored.append(tool_message)

            self.save_messages(CONVERSATION_ID, stored)
                
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
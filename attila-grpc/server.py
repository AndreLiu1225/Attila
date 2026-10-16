import gateway_pb2
import gateway_pb2_grpc
from harness.harness import run_tool, call_model

import grpc
from concurrent import futures
from utils.database import Database
from roles.role import Role

CONVERSATION_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "00000000-0000-0000-0000-000000000001"

class GatewayServicer(gateway_pb2_grpc.AttilaGatewayServicer):
    def __init__(self):
        self.db = Database()

    def Health(self, request, context):
        return gateway_pb2.HealthResponse(
            status=gateway_pb2.StatusType.STATUS_ACTIVE
        )

    def ListMessages(self, request, context):
        response = gateway_pb2.ListMessagesResponse()
        rows = self.db.list_messages(CONVERSATION_ID)
        for row in rows:
            item = response.messages.add()
            item.id = row["id"]
            item.sender = row["sender"]
            item.content = row["content"]
        return response

    def RunAgent(self, request_iterator, context):
        self.db.ensure_conversation(USER_ID, CONVERSATION_ID)
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

        # TODO: Edit messages to be prepared context after compaction
        messages = [{"role": Role.USER, "content": request.prompt}]

        self.db.save_message(CONVERSATION_ID, Role.CLIENT, request.prompt)

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
                self.db.save_message(CONVERSATION_ID, Role.AGENT, reply.text)
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
                    "role": Role.TOOL,
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
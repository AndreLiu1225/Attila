import grpc
from concurrent import futures
import time
import gateway_pb2
import gateway_pb2_grpc
from harness.harness import run_tool, call_model


class GatewayServicer(gateway_pb2_grpc.AttilaGatewayServicer):
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

    def RunAgent(self, request, context):
        print("Run Agent Request Made:")
        print(request)
        messages = [{"role": "user", "content": request.prompt}]

        for step in range(1, 10):
            yield gateway_pb2.AgentEvent(
                run_id=request.run_id,
                model_started=gateway_pb2.ModelStarted(
                    model_name="gpt-4.1-mini",
                    step_number=step
                ),
            )

            reply = call_model(messages)

            yield gateway_pb2.AgentEvent(
                run_id=request.run_id,
                model_finished=gateway_pb2.ModelFinished(
                    text=reply.text,
                    tool_calls=reply.tool_calls,
                ),
            )

            if not reply.tool_calls:
                yield gateway_pb2.AgentEvent(
                    run_id=request.run_id,
                    run_completed=gateway_pb2.RunCompleted(final_text=reply.text)
                )
                return

            for call in reply.tool_calls:
                yield gateway_pb2.AgentEvent(
                    run_id=request.run_id,
                    tool_started=gateway_pb2.ToolStarted(
                        tool_call_id=call.tool_call_id,
                        name=call.name,
                        arguments_json=call.arguments_json,
                    ),
                )
                output = run_tool(call.name, call.arguments_json)
                yield gateway_pb2.AgentEvent(
                    run_id=request.run_id,
                    tool_finished=gateway_pb2.ToolFinished(
                        tool_call_id=call.tool_call_id,
                        name=call.name,
                        output=output,
                        ok=True,
                    ),
                )
                messages.append({"role": "tool", "content": output})

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
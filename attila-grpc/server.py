import grpc
from concurrent import futures
import time
import gateway_pb2
import gateway_pb2_grpc


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

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    gateway_pb2_grpc.add_AttilaGatewayServicer_to_server(GatewayServicer(), server)
    server.add_insecure_port("localhost:50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
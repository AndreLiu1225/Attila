import grpc

import gateway_pb2
import gateway_pb2_grpc


def run():
    channel = grpc.insecure_channel("localhost:50051")
    stub = gateway_pb2_grpc.AttilaGatewayStub(channel)

    # 1. Test Health RPC
    health_response = stub.Health(
        gateway_pb2.HealthRequest()
    )

    print("Health:")
    print(health_response)


if __name__ == "__main__":
    run()

# Attila (A Electron Desktop AI Agentic App)
Attila is a side project aiming to explore the development of Agentic AI Applications with industry-standard microservices frameworks such as gRPC.

# Overview
Attila could be seen as a stepping stone for other developers interested in developing their own Agentic AI Applications. It features a gRPC backend found in `attila-grpc/` and an Electron frontend found in `attila-electron/`. The architecture features a *bidirectional stream* defined in the protobuf file `./protos/gateway.proto` under the function `rpc RunAgent(stream Client) returns (stream AgentEvent)`. The reason for setting up a bidirectional stream is so that command outputs could be sent back to the *agent harness* for further generation of commands if needed.

# Functional Requirements (Implemented)
- As a user, I'm able to run browser search tasks.
- As a user, I'm able to ask the agent to run any commands in my working directory.
- As a user, I'm able to view my conversation history (partially implemented)

# References
You may find it useful to replicate this project with these tutorials:

- MissCoding's exceptionally concise youtube tutorial explaining how to get started with gRPC: https://www.youtube.com/watch?v=WB37L7PjI5k&t=158s
- Also freeCodeCamp.org for their comprehensive guide on how to get started with Electron: https://www.youtube.com/watch?v=fP-371MN0Ck&t=10521s


# Usage

To run gRPC server:
`cd attila-grpc`
`python3 server.py`

To run Electron desktop app:
`cd attila-electron`
`npm run dev`

To configure your own gRPC protocol, edit the `./protos/gateway.proto` file and run:
`python3 -m grpc_tools.protoc -I protos --python_out=. --grpc_python_out=. protos/gateway.proto`

to recompile grpc gateway_pb2 and gateway_pb2_grpc

# Installation
`cd attila-grpc`
`pip install -r requirements.txt`

# Discussion
Feel free to head over to the discussions tab or open issues for bugs/feature requests!


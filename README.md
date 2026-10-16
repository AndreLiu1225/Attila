
# Attila (A Electron Desktop AI Agentic App)
Attila is a side project aiming to explore the development of Agentic AI Applications with industry-standard microservices frameworks such as gRPC.

# Overview
Attila could be seen as a stepping stone for other developers interested in developing their own Agentic AI Applications. It features a gRPC backend found in `attila-grpc/` and an Electron frontend found in `attila-electron/`. The architecture features a *bidirectional stream* defined in the protobuf file `./protos/gateway.proto` under the function `rpc RunAgent(stream Client) returns (stream AgentEvent)`. The reason for setting up a bidirectional stream is so that command outputs could be sent back to the *agent harness* for further generation of commands if needed.

# Functional Requirements (Implemented)
- As a user, I'm able to run browser search tasks.
- As a user, I'm able to ask the agent to run any commands in my working directory.
- As a user, I'm able to view my conversation history (partially implemented)

# Database
Conversation history is stored in the PostgreSQL database `attila`. The `vector` extension (pgvector) is installed in that database. A user owns many conversations, and each conversation owns many messages. Deleting a user deletes that user's conversations, and deleting a conversation deletes its messages.

## `users`

| Column | Type | Nullable | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | no | `gen_random_uuid()` | Primary key |
| `created_at` | `timestamptz` | no | `now()` | |

## `conversations`

| Column | Type | Nullable | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | no | `gen_random_uuid()` | Primary key |
| `user_id` | `uuid` | no | | Foreign key to `users.id`, `ON DELETE CASCADE` |
| `created_at` | `timestamptz` | no | `now()` | |

## `messages`

| Column | Type | Nullable | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | `bigint` | no | identity | Primary key |
| `conversation_id` | `uuid` | no | | Foreign key to `conversations.id`, `ON DELETE CASCADE` |
| `sender` | `text` | no | | Check: `client` or `agent` |
| `content` | `text` | no | | |
| `embedding` | `vector(1024)` | yes | | Embedding of `content` from `Qwen/Qwen3-Embedding-0.6B` |
| `created_at` | `timestamptz` | no | `now()` | |

`embedding` is nullable so a message can be stored when the embedding request fails. Similarity search should skip those rows with `embedding IS NOT NULL`.

## Indexes

| Index | Table | Method | Columns | Purpose |
| --- | --- | --- | --- | --- |
| `users_pkey` | `users` | btree, unique | `id` | Primary key lookup |
| `conversations_pkey` | `conversations` | btree, unique | `id` | Primary key lookup |
| `conversations_user_idx` | `conversations` | btree | `user_id`, `created_at` | List one user's conversations in time order |
| `messages_pkey` | `messages` | btree, unique | `id` | Primary key lookup |
| `messages_conversation_idx` | `messages` | btree | `conversation_id`, `created_at` | Load a conversation's recent messages in time order |
| `messages_embedding_idx` | `messages` | HNSW (`vector_cosine_ops`) | `embedding` | Nearest-message search by cosine distance (`<=>`) |

# Compaction
Each new prompt is sent to Groq with a small slice of older history. The full transcript stays in `messages` and is what the Electron app loads through `ListMessages`. The compacted slice is only the context for the model.

## Embedding
`attila-grpc/harness/compaction.py` loads `Qwen/Qwen3-Embedding-0.6B` with FastEmbed. That model returns 1024 floats, which is the width of `messages.embedding`. `generate_vector` embeds the first 24,000 characters of the text. The `content` column still stores the full message. Named-entity extraction is not used: the vector width is fixed by the model, and the whole message is what similarity search should see.

## What one run sends to the model
`RunAgent` keeps an in-memory `messages` list because Groq does not remember the previous call. Compaction only decides how that list starts.

1. Embed the new prompt.
2. Load the five nearest stored rows in that conversation. `fetch_related_messages` uses cosine distance (`<=>`) and skips rows whose `embedding` is null:

```sql
SELECT id, sender, content, created_at
FROM messages
WHERE conversation_id = %s
  AND embedding IS NOT NULL
ORDER BY embedding <=> %s
LIMIT 5
```

3. Sort those five by `created_at`, then `id`, so the model sees them in time order.
4. Map `client` to the model role `user`, and `agent` to `assistant`.
5. Append the new prompt as `user`.
6. Insert the prompt and its embedding after that search, so the new row is not returned as its own nearest neighbor.
7. If the model calls a tool, append the assistant tool request and the tool result to the in-memory list for the next step. Tool output is not embedded and is not written to `messages`.
8. When the model returns a final answer, embed that text and insert it with sender `agent`.

The tool loop can still grow during the current run. It stops after 10 steps, and the Electron client caps each bash result at 8,000 characters. The five retrieved rows are what keep older history inside a small token budget.

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


import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import path from 'path';
import { fileURLToPath } from 'url';
import { randomUUID } from 'crypto';
import { spawn } from 'child_process';

const dir = path.dirname(fileURLToPath(import.meta.url));
const PROTO_PATH = path.join(dir, '../../attila-grpc/protos/gateway.proto');

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
});

const gatewayProto = grpc.loadPackageDefinition(packageDefinition).gateway as any;

function createClient() {
    return new gatewayProto.AttilaGateway(
        'localhost:50051',
        grpc.credentials.createInsecure(),
    );
}

export async function getHealthResponse(): Promise<HealthResponse> {
    const client = createClient();

    return new Promise<HealthResponse>((resolve, reject) => {
        client.Health({ request_id: randomUUID() }, (err: Error | null, response: HealthResponse) => {
            if (err) reject(err);
            else resolve(response);
        });
    });
}

export async function runAgent(prompt: string): Promise<AgentEvent[]> {
    const client = createClient();

    return new Promise<AgentEvent[]>((resolve, reject) => {
        const events: AgentEvent[] = [];
        const stream = client.RunAgent();

        stream.on('data', async (event: AgentEvent) => {
            events.push(event);

            if (event.event === "tool_started" && event.tool_started?.name === 'bash') {
                const args = JSON.parse(event.tool_started.arguments_json || '{}') as { query?: string };
                const result = await runBash(args.query ?? '');
                stream.write({
                    tool_result: {
                        tool_call_id: event.tool_started.tool_call_id,
                        output: result.output,
                        ok: result.ok
                    }
                });
            }
        });

        stream.on('error', reject);
        stream.on('end', () => resolve(events));

        stream.write({
            run_request: {
                run_id: randomUUID(),
                prompt,
            }
        })
    });
}

function runBash(command: string): Promise<{ output: string; ok: boolean }> {
  return new Promise((resolve) => {
    const child = spawn('bash', ['-lc', command], { cwd: process.cwd() });
    let output = '';
    const append = (chunk: Buffer) => {
      output = (output + chunk.toString()).slice(0, 8000);
    };
    child.stdout.on('data', append);
    child.stderr.on('data', append);
    const timer = setTimeout(() => {
      child.kill();
      resolve({ output: `${output}\n(timed out)`, ok: false });
    }, 15_000);
    child.on('close', (code) => {
      clearTimeout(timer);
      resolve({ output, ok: code === 0 });
    });
  });
}

import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import path from 'path';
import { fileURLToPath } from 'url';
import { randomUUID } from 'crypto';

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

export async function getTaskResponse(content: string): Promise<TaskResponse[]> {
    const client = createClient();

    return new Promise<TaskResponse[]>((resolve, reject) => {
        const responses: TaskResponse[] = [];
        const stream = client.SubmitTask({
            request_id: randomUUID(),
            content,
            type: 'PROMPT_EVENT',
        });

        stream.on('data', (response: TaskResponse) => {
            responses.push(response);
        });
        stream.on('error', reject);
        stream.on('end', () => resolve(responses));
    });
}

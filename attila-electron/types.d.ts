type Statistics = {
    cpuUsage: number;
    ramUsage: number;
    storageData: number;
};

type StaticData = {
    totalStorage: number;
    cpuModel: string;
    totalMemoryGB: number;
};

type HealthResponse = {
    status: string;
};

type ToolCall = {
    tool_call_id: string;
    name: string;
    arguments_json: string;
};

type AgentEventKind =
    | 'run_started'
    | 'model_started'
    | 'model_finished'
    | 'tool_started'
    | 'tool_finished'
    | 'run_completed'
    | 'run_failed';

type AgentEvent = {
    run_id: string;
    event: AgentEventKind;
    run_started?: { prompt: string };
    model_started?: { model_name: string; step_number: number };
    model_finished?: { text: string; tool_calls?: ToolCall[] };
    tool_started?: { tool_call_id: string; name: string; arguments_json: string };
    tool_finished?: { tool_call_id: string; name: string; output: string; ok: boolean };
    run_completed?: { final_text: string };
    run_failed?: { message: string };
};

type View = 'CPU' | 'RAM' | 'STORAGE';

type FrameWindowAction = 'CLOSE' | 'MAXIMIZE' | 'MINIMIZE';

type EventPayloadMapping = {
    statistics: Statistics;
    getStaticData: StaticData;
    changeView: View;
    sendFrameAction: FrameWindowAction;
    getHealthResponse: HealthResponse;
    runAgent: AgentEvent[];
};

type UnsubscribeFunction = () => void;

interface Window {
    electron: {
        subscribeStatistics: (
            callback: (statistics: Statistics) => void
        ) => UnsubscribeFunction;
        getStaticData: () => Promise<StaticData>;
        subscribeChangeView: (
            callback: (view: View) => void
        ) => UnsubscribeFunction;
        sendFrameAction: (payload: FrameWindowAction) => void;
        getHealthResponse: () => Promise<HealthResponse>;
        runAgent: (prompt: string) => Promise<AgentEvent[]>;
    };
}

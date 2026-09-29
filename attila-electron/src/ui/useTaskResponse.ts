import { useState } from 'react';

type TimelineItem = 
    | {
        kind: 'tool';
        id: string;
        label: string;
        output?: string;
        pending: boolean;
    }
    | {
        kind: 'answer';
        markdown: string;
    };

export function toTimeline(events: AgentEvent[]): TimelineItem[] {
    const items: TimelineItem[] = [];

    for (const event of events) {
    if (event.event === 'tool_started' && event.tool_started) {
        items.push({
            kind: 'tool',
            id: event.tool_started.tool_call_id,
            label: toolLabel(event.tool_started.name, event.tool_started.arguments_json),
            pending: true,
        });
    }
    if (event.event === 'tool_finished' && event.tool_finished) {
        const row = items.find(
            (item) => item.kind === 'tool' && item.id === event.tool_finished?.tool_call_id
        );
        if (row && row.kind === 'tool') {
            row.output = event.tool_finished.output;
            row.pending = false;
        }
    }
    if (event.event === 'run_completed') {
        items.push({
            kind: 'answer',
            markdown: event.run_completed?.final_text ?? '',
        });
    }
    }
    return items;
}

function toolLabel(name: string, argumentsJson: string): string {
    const args = JSON.parse(argumentsJson || '{}') as { query?: string };

    if (name === 'web_search') {
        return `Searched the web for "${args.query ?? ''}"`;
    }

    if (name === 'bash') {
        return `Ran \`${args.query ?? ''}\``;
    }

    return `Used ${name}`;
}

export function formatAgentEvent(event: AgentEvent): string {
    switch (event.event) {
        case 'run_started':
            return `Run started: ${event.run_started?.prompt ?? ''}`;
        case 'model_started':
            return `Model ${event.model_started?.model_name ?? ''} · step ${event.model_started?.step_number ?? ''}`;
        case 'model_finished': {
            const calls = event.model_finished?.tool_calls ?? [];
            const text = event.model_finished?.text ?? '';
            if (calls.length === 0) {
                return text;
            }
            const names = calls.map((call) => call.name).join(', ');
            return text ? `${text} (tools: ${names})` : `Calling ${names}`;
        }
        case 'tool_started':
            return `Tool started: ${event.tool_started?.name ?? ''}`;
        case 'tool_finished':
            return `Tool ${event.tool_finished?.name ?? ''}: ${event.tool_finished?.output ?? ''}`;
        case 'run_completed':
            return event.run_completed?.final_text ?? '';
        case 'run_failed':
            return `Failed: ${event.run_failed?.message ?? ''}`;
    }
}

export function useTaskResponse() {
    const [events, setEvents] = useState<AgentEvent[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    async function submitPrompt(content: string) {
        const trimmedPrompt = content.trim();
        if (!trimmedPrompt || isSubmitting) {
            return;
        }

        setIsSubmitting(true);
        setError(null);
        setEvents([]);

        try {
            const agentEvents = await window.electron.runAgent(trimmedPrompt);
            setEvents(agentEvents);
            const failed = agentEvents.find((event) => event.event === 'run_failed');
            if (failed?.run_failed?.message) {
                setError(failed.run_failed.message);
            }
        } catch (submitError) {
            setError(
                submitError instanceof Error
                    ? submitError.message
                    : 'Failed to run agent'
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    return { events, error, isSubmitting, submitPrompt };
}

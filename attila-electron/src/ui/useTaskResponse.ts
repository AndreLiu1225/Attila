import { useEffect, useState } from 'react';

function toolLabel(name: string, argumentsJson: string): string {
    const args = JSON.parse(argumentsJson || '{}') as { query?: string; cmd?: string };

    if (name === 'web_search') {
        return `Searched the web for "${args.query ?? ''}"`;
    }

    if (name === 'bash') {
        return `Ran \`${args.cmd ?? ''}\``;
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
    const [items, setItems] = useState<ChatItem[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        return window.electron.subscribeAgentEvents((event) => {
            if (event.event === 'tool_started' && event.tool_started) {
                const started = event.tool_started;
                setItems((prev) => [
                    ...prev,
                    {
                        kind: 'tool',
                        id: started.tool_call_id,
                        label: toolLabel(started.name, started.arguments_json),
                        pending: true,
                    },
                ]);
            }
            if (event.event === 'tool_finished' && event.tool_finished) {
                const finished = event.tool_finished;
                setItems((prev) =>
                    prev.map((item) =>
                        item.kind === 'tool' && item.id === finished.tool_call_id
                            ? { ...item, output: finished.output, pending: false }
                            : item,
                    ),
                );
            }
            if (event.event === 'run_completed') {
                setItems((prev) => [
                    ...prev,
                    {
                        kind: 'answer',
                        id: crypto.randomUUID(),
                        markdown: event.run_completed?.final_text ?? '',
                    },
                ]);
            }
            if (event.event === 'run_failed') {
                setError(event.run_failed?.message ?? 'Run failed');
            }
        });
    }, []);

    async function submitPrompt(content: string) {
        const trimmedPrompt = content.trim();
        if (!trimmedPrompt || isSubmitting) {
            return;
        }

        setIsSubmitting(true);
        setError(null);
        setItems((prev) => [
            ...prev,
            { kind: 'user', id: crypto.randomUUID(), text: trimmedPrompt },
        ]);

        try {
            await window.electron.runAgent(trimmedPrompt);
        } catch (submitError) {
            setError(
                submitError instanceof Error
                    ? submitError.message
                    : 'Failed to run agent',
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    return { items, error, isSubmitting, submitPrompt };
}

import { useState } from 'react';

export function useTaskResponse() {
    const [responses, setResponses] = useState<TaskResponse[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    async function submitPrompt(content: string) {
        const trimmedPrompt = content.trim();
        if (!trimmedPrompt || isSubmitting) {
            return;
        }

        setIsSubmitting(true);
        setError(null);
        setResponses([]);

        try {
            const taskResponses = await window.electron.getTaskResponse(trimmedPrompt);
            setResponses(taskResponses);
        } catch (submitError) {
            setError(
                submitError instanceof Error
                    ? submitError.message
                    : 'Failed to submit prompt'
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    return { responses, error, isSubmitting, submitPrompt };
}

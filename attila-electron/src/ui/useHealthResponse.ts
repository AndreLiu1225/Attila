import { useEffect, useState } from "react";

export function useHealthResponse() {
    const [health, setHealth] = useState<HealthResponse | null>(null);

    useEffect(() => {
        (async () => {
            setHealth(await window.electron.getHealthResponse());
        })();
    }, []);

    return health;
}
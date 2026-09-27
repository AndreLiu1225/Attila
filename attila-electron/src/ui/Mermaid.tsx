import { useEffect, useId, useState } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({ startOnLoad: false, theme: 'dark' });

export function Mermaid({ chart }: { chart: string }) {
  const reactId = useId().replace(/:/g, '');
  const [svg, setSvg] = useState('');

  useEffect(() => {
    let cancelled = false;
    mermaid
      .render(`diagram-${reactId}`, chart)
      .then(({ svg: nextSvg }) => {
        if (!cancelled) setSvg(nextSvg);
      })
      .catch(() => {
        if (!cancelled) setSvg('');
      });
    return () => {
      cancelled = true;
    };
  }, [chart, reactId]);

  if (!svg) {
    return <pre>{chart}</pre>;
  }

  return <div dangerouslySetInnerHTML={{ __html: svg }} />;
}
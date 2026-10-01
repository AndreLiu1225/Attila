import { useEffect, useRef, useState, type ComponentProps } from 'react';
import './App.css';
import { useTaskResponse } from './useTaskResponse';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Mermaid } from './Mermaid';

export function Markdown({ markdown }: { markdown: string }) {
  return (
    <div className="answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children }) {
            const text = String(children).replace(/\n$/, '');
            if (className === 'language-mermaid') {
              return <Mermaid chart={text} />;
            }
            return <code className={className}>{text}</code>;
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

function App() {
  const { items, error, isSubmitting, submitPrompt } = useTaskResponse();
  const [prompt, setPrompt] = useState('');
  const transcriptRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (transcript && stickToBottom.current) {
      transcript.scrollTop = transcript.scrollHeight;
    }
  }, [items]);

  function handleScroll() {
    const transcript = transcriptRef.current;
    if (!transcript) {
      return;
    }
    const distanceFromBottom =
      transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight;
    stickToBottom.current = distanceFromBottom < 80;
  }

  const handlePromptSubmit: NonNullable<ComponentProps<'form'>['onSubmit']> = async (event) => {
    event.preventDefault();
    const sent = prompt;
    setPrompt('');
    stickToBottom.current = true;
    await submitPrompt(sent);
  };

  return (
    <div className="App">
      <Header />
      <section className="chat">
        <div className="transcript" ref={transcriptRef} onScroll={handleScroll}>
          {items.map((item) => {
            if (item.kind === 'user') {
              return (
                <article key={item.id} className="bubble user">
                  <p>{item.text}</p>
                </article>
              );
            }
            if (item.kind === 'tool') {
              return (
                <details key={item.id} className="toolRow" open={item.pending}>
                  <summary>{item.pending ? 'Searching…' : item.label}</summary>
                  {item.output && <pre className="toolOutput">{item.output}</pre>}
                </details>
              );
            }
            return (
              <article key={item.id} className="bubble agent">
                <Markdown markdown={item.markdown} />
              </article>
            );
          })}
        </div>
        <form className="promptForm" onSubmit={handlePromptSubmit}>
          <input
            className="promptInput"
            type="text"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Ask Attila anything..."
            disabled={isSubmitting}
          />
          <button className="promptSubmit" type="submit" disabled={isSubmitting || !prompt.trim()}>
            {isSubmitting ? 'Waiting...' : 'Submit'}
          </button>
        </form>
        {error && <p className="promptError">{error}</p>}
      </section>
    </div>
  );
}

function Header() {
  return (
    <header>
      <button
        id="close"
        onClick={() => window.electron.sendFrameAction('CLOSE')}
      />
      <button
        id="minimize"
        onClick={() => window.electron.sendFrameAction('MINIMIZE')}
      />
      <button
        id="maximize"
        onClick={() => window.electron.sendFrameAction('MAXIMIZE')}
      />
    </header>
  );
}

export default App;

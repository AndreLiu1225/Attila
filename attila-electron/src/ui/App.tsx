import { useState, type ComponentProps } from 'react';
import './App.css';
import { toTimeline, useTaskResponse } from './useTaskResponse';
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
  const { events, error, isSubmitting, submitPrompt } = useTaskResponse();
  const [prompt, setPrompt] = useState('');

  const handlePromptSubmit: NonNullable<ComponentProps<'form'>['onSubmit']> = async (event) => {
    event.preventDefault();
    await submitPrompt(prompt);
  };

  return (
    <div className="App">
      <Header />
      <section className="promptSection">
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
        {events.length > 0 && (
          <div className="promptResponses">
            {toTimeline(events).map((item, index) =>
              item.kind === 'tool' ? (
                <details key={item.id} className="toolRow" open={item.pending}>
                  <summary>{item.pending ? 'Searching…' : item.label}</summary>
                  {item.output && <pre className="toolOutput">{item.output}</pre>}
                </details>
              ) : (
                <Markdown key={`answer-${index}`} markdown={item.markdown} />
              )
            )}
          </div>
        )}
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

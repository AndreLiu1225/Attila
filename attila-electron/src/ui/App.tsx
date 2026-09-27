import { useEffect, useMemo, useState, type ComponentProps } from 'react';
import './App.css';
import { useStatistics } from './useStatistics';
import { Chart } from './Chart';
import { useHealthResponse } from './useHealthResponse';
import { useTaskResponse } from './useTaskResponse';

function App() {
  const staticData = useStaticData();
  const statistics = useStatistics(10);
  const health = useHealthResponse();
  const { responses, error, isSubmitting, submitPrompt } = useTaskResponse();
  const [activeView, setActiveView] = useState<View>('CPU');
  const [prompt, setPrompt] = useState('');
  const cpuUsages = useMemo(
    () => statistics.map((stat) => stat.cpuUsage),
    [statistics]
  );
  const ramUsages = useMemo(
    () => statistics.map((stat) => stat.ramUsage),
    [statistics]
  );
  const storageUsages = useMemo(
    () => statistics.map((stat) => stat.storageData),
    [statistics]
  );
  const activeUsages = useMemo(() => {
    switch (activeView) {
      case 'CPU':
        return cpuUsages;
      case 'RAM':
        return ramUsages;
      case 'STORAGE':
        return storageUsages;
    }
  }, [activeView, cpuUsages, ramUsages, storageUsages]);

  useEffect(() => {
    return window.electron.subscribeChangeView((view) => setActiveView(view));
  }, []);

  const handlePromptSubmit: NonNullable<ComponentProps<'form'>['onSubmit']> = async (event) => {
    event.preventDefault();
    await submitPrompt(prompt);
  };

  return (
    <div className="App">
      <Header />
      <div className="statusBar">
        <p>Server status: {health?.status ?? 'loading...'}</p>
      </div>
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
        {responses.length > 0 && (
          <div className="promptResponses">
            {responses.map((taskResponse, index) => (
              <p key={`${taskResponse.request_id}-${index}`} className="promptResponse">
                {taskResponse.response}
              </p>
            ))}
          </div>
        )}
      </section>
      <div className="main">
        <div>
          <SelectOption
            onClick={() => setActiveView('CPU')}
            title="CPU"
            view="CPU"
            subTitle={staticData?.cpuModel ?? ''}
            data={cpuUsages}
          />
          <SelectOption
            onClick={() => setActiveView('RAM')}
            title="RAM"
            view="RAM"
            subTitle={(staticData?.totalMemoryGB.toString() ?? '') + ' GB'}
            data={ramUsages}
          />
          <SelectOption
            onClick={() => setActiveView('STORAGE')}
            title="STORAGE"
            view="STORAGE"
            subTitle={(staticData?.totalStorage.toString() ?? '') + ' GB'}
            data={storageUsages}
          />
        </div>
        <div className="mainGrid">
          <Chart
            selectedView={activeView}
            data={activeUsages}
            maxDataPoints={10}
          />
        </div>
      </div>
    </div>
  );
}

function SelectOption(props: {
  title: string;
  view: View;
  subTitle: string;
  data: number[];
  onClick: () => void;
}) {
  return (
    <button className="selectOption" onClick={props.onClick}>
      <div className="selectOptionTitle">
        <div>{props.title}</div>
        <div>{props.subTitle}</div>
      </div>
      <div className="selectOptionChart">
        <Chart selectedView={props.view} data={props.data} maxDataPoints={10} />
      </div>
    </button>
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

function useStaticData() {
  const [staticData, setStaticData] = useState<StaticData | null>(null);

  useEffect(() => {
    (async () => {
      setStaticData(await window.electron.getStaticData());
    })();
  }, []);

  return staticData;
}

export default App;

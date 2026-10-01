import { app, BrowserWindow, ipcMain } from 'electron';
import { ipcMainHandle, ipcMainOn, ipcWebContentsSend, isDev, validateEventFrame } from './util.js';
import { getStaticData, pollResources } from './resourceManager.js';
import { getPreloadPath, getUIPath } from './pathResolver.js';
import { createTray } from './tray.js';
import { createMenu } from './menu.js';
import { getHealthResponse, runAgent } from './grpcClient.js';

app.on('ready', async () => {
    const mainWindow = new BrowserWindow({
        webPreferences: {
            preload: getPreloadPath(),
        },
        frame: false,
    });
    if (isDev()) {
        mainWindow.loadURL('http://localhost:5123');
    } else {
        mainWindow.loadFile(getUIPath());
    }

    pollResources(mainWindow);

    ipcMainHandle('getStaticData', () => {
        return getStaticData();
    });

    ipcMainHandle('getHealthResponse', () => {
        return getHealthResponse();
    });

    ipcMain.handle('runAgent', (event, payload) => {
        validateEventFrame(event.senderFrame!);
        const request = payload as { prompt: string };
        return runAgent(request.prompt, (agentEvent) => {
            ipcWebContentsSend('agentEvent', event.sender, agentEvent);
        });
    });

    ipcMainOn('sendFrameAction', (payload) => {
        switch (payload) {
            case 'CLOSE':
                mainWindow.close();
                break;
            case 'MAXIMIZE':
                mainWindow.maximize();
                break;
            case 'MINIMIZE':
                mainWindow.minimize();
                break;
        }
    });

    createTray(mainWindow);
    handleCloseEvents(mainWindow);
    createMenu(mainWindow);
});

function handleCloseEvents(mainWindow: BrowserWindow) {
    let willClose = false;

    mainWindow.on('close', (e) => {
        if (willClose) {
            return;
        }
        e.preventDefault();
        mainWindow.hide();
        if (app.dock) {
            app.dock.hide();
        }
    });

    app.on('before-quit', () => {
        willClose = true;
    });

    mainWindow.on('show', () => {
        willClose = false;
    });
}

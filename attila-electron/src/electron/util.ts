import { ipcMain, WebContents, WebFrameMain } from 'electron';
import { pathToFileURL } from 'url';
import { getUIPath } from './pathResolver.js';

export function isDev(): boolean {
    return process.env.NODE_ENV === 'development';
}

export function ipcMainHandle<Key extends keyof EventPayloadMapping>(
    key: Key,
    handler: (payload?: unknown) => EventPayloadMapping[Key] | Promise<EventPayloadMapping[Key]>
) {
    ipcMain.handle(key, (event, payload) => {
        validateEventFrame(event.senderFrame!);
        return handler(payload);
    });
}

export function ipcMainOn<Key extends keyof EventPayloadMapping>(
    key: Key,
    handler: (payload: EventPayloadMapping[Key]) => void
) {
    ipcMain.on(key, (event, payload) => {
        if (event.senderFrame) {
            validateEventFrame(event.senderFrame);
        } else {
            validateSenderUrl(event.sender.getURL());
        }
        handler(payload);
    });
}

export function ipcWebContentsSend<Key extends keyof EventPayloadMapping>(
    key: Key,
    webContents: WebContents,
    payload: EventPayloadMapping[Key]
) {
    webContents.send(key, payload);
}

export function validateEventFrame(frame: WebFrameMain) {
    validateSenderUrl(frame.url);
}

function validateSenderUrl(url: string) {
    if (isDev() && new URL(url).host === 'localhost:5123') {
        return;
    }
    if (url !== pathToFileURL(getUIPath()).toString()) {
        throw new Error('Malicious event');
    }
}

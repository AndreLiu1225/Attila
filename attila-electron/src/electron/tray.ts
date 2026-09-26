import { app, BrowserWindow, Menu, Tray, nativeImage } from 'electron';
import path from 'path';
import { getAssetPath } from './pathResolver.js';

let tray: Tray | undefined;

export function createTray(mainWindow: BrowserWindow) {
    const iconPath = path.join(
        getAssetPath(),
        process.platform === 'darwin' ? 'trayIconTemplate.png' : 'trayIcon.png'
    );

    const image = nativeImage.createFromPath(iconPath);

    if (image.isEmpty()) {
        throw new Error(`Tray icon not found at ${iconPath}`);
    }

    tray = new Tray(image);
    tray.setToolTip('Attila');

    tray.setContextMenu(
        Menu.buildFromTemplate([
            {
                label: 'Show',
                click: () => {
                    mainWindow.show();
                    if (app.dock) {
                        app.dock.show();
                    }
                },
            },
            {
                label: 'Quit',
                click: () => app.quit(),
            },
        ])
    );
}

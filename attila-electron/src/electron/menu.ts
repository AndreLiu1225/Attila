import { app, BrowserWindow, Menu } from "electron";
import { isDev } from "./util.js";

export function createMenu(mainWindow: BrowserWindow) {
    Menu.setApplicationMenu(Menu.buildFromTemplate([
        {
            label: process.platform === 'darwin' ? undefined : 'Attila',
            type: "submenu",
            submenu: [
                {
                    label: "Quit",
                    click: app.quit,
                },
                {
                    label: "DevTools",
                    click: () => mainWindow.webContents.openDevTools(),
                    visible: isDev(),
                },
            ],
        },
    ]));
}
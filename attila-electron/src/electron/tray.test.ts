import { expect, test, vi, type Mock } from 'vitest';
import { createTray } from './tray.js';
import { app, Menu, type BrowserWindow } from 'electron';

vi.mock('./pathResolver.js', () => ({
  getAssetPath: vi.fn().mockReturnValue('/assets'),
}));

vi.mock('electron', () => {
  return {
    Tray: vi.fn().mockReturnValue({
      setContextMenu: vi.fn(),
      setToolTip: vi.fn(),
    }),
    nativeImage: {
      createFromPath: vi.fn().mockReturnValue({
        isEmpty: () => false,
        setTemplateImage: vi.fn(),
      }),
    },
    app: {
      getAppPath: vi.fn().mockReturnValue('/'),
      dock: {
        show: vi.fn(),
      },
      quit: vi.fn(),
    },
    Menu: {
      buildFromTemplate: vi.fn(),
    },
  };
});

const mainWindow = {
  show: vi.fn(),
} as unknown as BrowserWindow;

test('tray context menu Show and Quit handlers work', () => {
  createTray(mainWindow);

  const calls = (Menu.buildFromTemplate as Mock).mock.calls;
  const template = calls[0][0] as Parameters<typeof Menu.buildFromTemplate>[0];
  expect(template).toHaveLength(2);

  expect(template[0].label).toEqual('Show');
  template[0]?.click?.(null as never, null as never, null as never);
  expect(mainWindow.show).toHaveBeenCalled();
  expect(app.dock!.show).toHaveBeenCalled();

  template[1]?.click?.(null as never, null as never, null as never);
  expect(app.quit).toHaveBeenCalled();
});

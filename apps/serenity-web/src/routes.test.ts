import { describe, expect, it } from 'vitest';

import { coreRoutes } from './routes';

describe('coreRoutes', () => {
  it('contains only Phase 5 Serenity-owned workbench routes', () => {
    expect(coreRoutes).toEqual([
      { path: '/', label: 'Home' },
      { path: '/analysis', label: 'Analysis' },
      { path: '/history', label: 'History' },
      { path: '/settings', label: 'Settings' },
    ]);

    const serializedRoutes = JSON.stringify(coreRoutes).toLowerCase();
    const externalSourcePackage = ['daily', 'stock', 'analysis'].join('_');
    const externalSourceApp = ['dsa', 'web'].join('-');

    expect(serializedRoutes).not.toContain('chat');
    expect(serializedRoutes).not.toContain('portfolio');
    expect(serializedRoutes).not.toContain('backtest');
    expect(serializedRoutes).not.toContain('alerts');
    expect(serializedRoutes).not.toContain(externalSourcePackage);
    expect(serializedRoutes).not.toContain(externalSourceApp);
  });
});

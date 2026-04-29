/**
 * @file tests/unit/lib/widgets/registry.test.ts
 * @brief Unit tests for the widget registry module.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  register,
  getDef,
  listDefs,
  clearRegistry,
  type WidgetDef,
} from '@/lib/widgets/registry';
import React from 'react';

const _noop = () => React.createElement('div');

function makeDef(id: string, category: WidgetDef['category'] = 'core', title = id): WidgetDef {
  return {
    id,
    title,
    defaultSize: 'md',
    category,
    Component: _noop,
  };
}

describe('widget registry', () => {
  beforeEach(() => {
    clearRegistry();
  });

  it('register adds def; listDefs returns it', () => {
    const def = makeDef('feed');
    register(def);
    const defs = listDefs();
    expect(defs).toHaveLength(1);
    expect(defs[0].id).toBe('feed');
  });

  it('duplicate id throws', () => {
    register(makeDef('feed'));
    expect(() => register(makeDef('feed'))).toThrowError(/already registered/);
  });

  it('getDef returns def when found', () => {
    const def = makeDef('feed');
    register(def);
    expect(getDef('feed')).toBe(def);
  });

  it('getDef returns undefined when not found', () => {
    expect(getDef('nonexistent')).toBeUndefined();
  });

  it('clearRegistry empties all registrations', () => {
    register(makeDef('feed'));
    register(makeDef('activity'));
    clearRegistry();
    expect(listDefs()).toHaveLength(0);
    expect(getDef('feed')).toBeUndefined();
  });

  it('listDefs sorts by category then title', () => {
    register(makeDef('z-widget', 'social', 'Zzz'));
    register(makeDef('a-widget', 'core', 'Aaa'));
    register(makeDef('m-widget', 'media', 'Mmm'));
    register(makeDef('b-widget', 'core', 'Bbb'));

    const defs = listDefs();
    expect(defs.map((d) => d.id)).toEqual(['a-widget', 'b-widget', 'm-widget', 'z-widget']);
  });
});

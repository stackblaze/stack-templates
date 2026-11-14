import * as migration_20261113_184040_initial from './20261113_184040_initial';

export const migrations = [
  {
    up: migration_20261113_184040_initial.up,
    down: migration_20261113_184040_initial.down,
    name: '20261113_184040_initial'
  },
];

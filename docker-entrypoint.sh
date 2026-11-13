#!/bin/sh
set -e

if [ "${ARKIVE_SKIP_MIGRATIONS:-0}" != "1" ]; then
  alembic upgrade head
fi

exec "$@"

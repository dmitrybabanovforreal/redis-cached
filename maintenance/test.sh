#!/usr/bin/env bash

set -e
set -x
export REDIS_CACHED_HOST="localhost"

pytest tests "${@}"

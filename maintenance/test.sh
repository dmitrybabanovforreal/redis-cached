#!/usr/bin/env bash

set -e
set -x
export REDIS_HOST="localhost"

pytest tests "${@}"

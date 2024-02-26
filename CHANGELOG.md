# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2024-02-26

### Changed

* The required env vars changed to the default redis format: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`.

## [0.2.1] - 2024-01-12

### Fixed

* Type annotation for the function parameters does not break when it's decorated.
* Assertion of the function being an async function happens during function definition now (e.g. when the module is imported) rather than every time the function is called.

## [0.2.0] - 2023-12-25

### Added

* Added a lock mechanism that shields the decorated function from multiple calls to update the cache when it experiences a cache miss during multiple concurrent calls.
* Falsy values (`None`, `''`, `[]`, etc.) are now cached as well.

## [0.1.0] - 2023-12-17

### Added

This is the initial release of the lib.

Python cache decorator that uses Redis or KeyDB as storage. This is very handy for replicated apps (e.g. Kubernetes), AWS Lambda functions, and other stateless apps.

Features:
* Writing to the cache happens asynchronously, so that you get the function result immediately.
* Function result and kwarg values are [pickled](https://docs.python.org/3/library/pickle.html), so you can work with complex structures like [pydantic](https://docs.pydantic.dev/latest/)'s `BaseModel`
* Cache invalidation is available

Limitations:
* Only async functions are supported.
* Only keyword arguments are supported. It will raise an error if you pass non-kwargs while calling your function.

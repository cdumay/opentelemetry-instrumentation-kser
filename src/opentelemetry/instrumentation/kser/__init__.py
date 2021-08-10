#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
.. codeauthor:: Cédric Dumay <cedric.dumay@gmail.com>


"""
import json
from typing import Collection

import kser.entry
import kser.sequencing.operation
from cdumay_result import Result
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.kser.package import _instruments
from opentelemetry.instrumentation.kser.version import __version__
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.trace import SpanKind, get_tracer
from wrapt import wrap_function_wrapper as _wrap


def _with_tracer_wrapper(func):
    """Helper for providing tracer for wrapper functions."""

    def _with_tracer(tracer):
        def wrapper(wrapped, instance, args, kwargs):
            return func(tracer, wrapped, instance, args, kwargs)

        return wrapper

    return _with_tracer


@_with_tracer_wrapper
def _wtrigger(tracer, wrapped, instance, args, kwargs):
    """Wrap task triggers"""
    trigger_name = wrapped.__name__
    if trigger_name.startswith('_'):
        trigger_name = trigger_name[1:]
    sname = f"{instance.__class__.__name__}[{instance.uuid}].{trigger_name}"
    with tracer.start_as_current_span(sname, kind=SpanKind.INTERNAL) as span:
        if span.is_recording():
            span.set_attribute('uuid', instance.uuid)
            span.set_attribute('status', instance.status)
            span.set_attribute('name', instance.__class__.path)
            span.set_attribute('trigger', trigger_name)

        result = wrapped(*args, **kwargs)
        if isinstance(result, Result):
            if span.is_recording():
                span.set_attribute("retcode", result.retcode)
                span.set_attribute("stdout", result.stdout)
                span.set_attribute("stderr", result.stderr)
                span.set_attribute("retval", json.dumps(result.retval))
        return result


class KserInstrumentor(BaseInstrumentor):
    """An instrumentor for jinja2
    See `BaseInstrumentor`
    """

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, __version__, tracer_provider)

        # tasks & operations
        _wrap(kser, "entry.Entrypoint._post_init", _wtrigger(tracer))
        _wrap(kser, "entry.Entrypoint._prerun", _wtrigger(tracer))
        _wrap(kser, "entry.Entrypoint._postrun", _wtrigger(tracer))
        _wrap(kser, "entry.Entrypoint._run", _wtrigger(tracer))
        _wrap(kser, "entry.Entrypoint.unsafe_execute", _wtrigger(tracer))
        _wrap(kser, "entry.Entrypoint._onsuccess", _wtrigger(tracer))
        _wrap(kser, "entry.Entrypoint._onerror", _wtrigger(tracer))

        # operations
        _wrap(
            kser, "sequencing.operation.Operation._prebuild",
            _wtrigger(tracer)
        )
        _wrap(
            kser, "sequencing.operation.Operation.build",
            _wtrigger(tracer)
        )
        _wrap(
            kser, "sequencing.operation.Operation.unsafe_execute",
            _wtrigger(tracer)
        )
        _wrap(
            kser, "sequencing.operation.Operation.compute_tasks",
            _wtrigger(tracer)
        )
        _wrap(
            kser, "sequencing.operation.Operation.finalize",
            _wtrigger(tracer)
        )
        _wrap(
            kser, "sequencing.operation.Operation._onsuccess",
            _wtrigger(tracer)
        )
        _wrap(
            kser, "sequencing.operation.Operation._onerror",
            _wtrigger(tracer)
        )

    def _uninstrument(self, **kwargs):
        unwrap(kser.entry.Entrypoint, "_post_init")
        unwrap(kser.entry.Entrypoint, "_prerun")
        unwrap(kser.entry.Entrypoint, "_postrun")
        unwrap(kser.entry.Entrypoint, "_run")
        unwrap(kser.entry.Entrypoint, "unsafe_execute")
        unwrap(kser.entry.Entrypoint, "_onsuccess")
        unwrap(kser.entry.Entrypoint, "_onerror")

        unwrap(kser.sequencing.operation.Operation, "_prebuild")
        unwrap(kser.sequencing.operation.Operation, "build")
        unwrap(kser.sequencing.operation.Operation, "unsafe_execute")
        unwrap(kser.sequencing.operation.Operation, "compute_tasks")
        unwrap(kser.sequencing.operation.Operation, "finalize")
        unwrap(kser.sequencing.operation.Operation, "_onsuccess")
        unwrap(kser.sequencing.operation.Operation, "_onerror")

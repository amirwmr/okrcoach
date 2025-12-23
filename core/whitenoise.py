from __future__ import annotations

from asgiref.sync import sync_to_async
from django.core.handlers.asgi import ASGIRequest
from whitenoise.middleware import WhiteNoiseMiddleware
from whitenoise.middleware import WhiteNoiseFileResponse as _WhiteNoiseFileResponse


class _DualIterator:
    """
    Iterator that supports both sync and async iteration over a file-like object.
    """

    def __init__(self, filelike, block_size: int):
        self.filelike = filelike
        self.block_size = block_size

    def __aiter__(self):
        return self

    async def __anext__(self):
        chunk = await sync_to_async(
            self.filelike.read, thread_sensitive=True
        )(self.block_size)
        if not chunk:
            raise StopAsyncIteration
        return chunk


class _AsyncFromSyncIterator:
    """
    Wrap a synchronous iterable to provide async iteration.
    """

    def __init__(self, iterable):
        self._iter = iter(iterable)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class AsyncWhiteNoiseFileResponse(_WhiteNoiseFileResponse):
    """
    FileResponse variant that provides an async iterator to avoid Django's ASGI warning.
    """

    def _set_streaming_content(self, value):
        if not hasattr(value, "read"):
            self.file_to_stream = None
            iterator = _AsyncFromSyncIterator(value)
            self._iterator = iterator
            self.is_async = True
            return iterator

        self.file_to_stream = filelike = value
        if hasattr(filelike, "close"):
            self._resource_closers.append(filelike.close)

        iterator = _DualIterator(filelike, self.block_size)
        self.set_headers(filelike)
        # Force async iteration to avoid Django's ASGI warning while keeping
        # the iterator usable in synchronous contexts.
        self._iterator = iterator
        self.is_async = True
        return iterator


class AsyncWhiteNoiseMiddleware(WhiteNoiseMiddleware):
    """
    Drop-in replacement for WhiteNoiseMiddleware that emits async-friendly responses.
    """

    @staticmethod
    def serve(static_file, request):
        response = static_file.get_response(request.method, request.META)
        status = int(response.status)
        is_asgi = isinstance(request, ASGIRequest) or hasattr(request, "scope")
        response_class = AsyncWhiteNoiseFileResponse if is_asgi else _WhiteNoiseFileResponse
        http_response = response_class(response.file or (), status=status)
        # Remove default content-type
        del http_response["content-type"]
        for key, value in response.headers:
            http_response[key] = value
        return http_response

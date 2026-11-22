"""All transport paths use HTTPX MockTransport, never the internet."""
import asyncio
import httpx
import pytest
from api_extractor.sse_sampling import _first_complete_message, sample_sse


def run(handler, url="https://app.example.com/api/stream", **kwargs):
    return asyncio.run(sample_sse(url, transport=httpx.MockTransport(handler), **kwargs))


def test_one_real_event_is_sampled_without_credentials():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, headers={"content-type":"text/event-stream; charset=utf-8"},
                              content=b':heartbeat\n\ndata: {"id": 1}\n\nmore: not included\n\n')
    result = run(handler)
    assert result.status == 200
    assert result.body == b':heartbeat\n\ndata: {"id": 1}\n\n'
    assert len(requests) == 1
    assert requests[0].method == 'GET'
    assert requests[0].headers['accept'] == 'text/event-stream'
    assert 'authorization' not in requests[0].headers
    assert 'cookie' not in requests[0].headers


def test_crlf_frame_complete():
    assert _first_complete_message(b':hello\r\n\r\ndata: hello\r\n\r\n') == b':hello\r\n\r\ndata: hello\r\n\r\n'


def test_only_comments_do_not_count_as_observed_message():
    assert _first_complete_message(b':one\n\n:two\n\n') is None


@pytest.mark.parametrize('status,ctype',[(302,'text/event-stream'),(401,'text/event-stream'),(200,'application/json'),(200,'text/html')])
def test_non_sse_or_redirect_never_proves_event(status,ctype):
    seen = []
    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(status,headers={'content-type':ctype,'location':'https://offscope.test/forbidden'}, content=b'data: fake\n\n')
    assert run(handler) is None
    assert len(seen) == 1  # no redirect follows


def test_no_complete_frame_is_rejected():
    assert run(lambda request: httpx.Response(200, headers={'content-type':'text/event-stream'},content=b'data: not complete')) is None


def test_oversized_frames_rejected_before_memory_expands():
    assert run(lambda request: httpx.Response(200, headers={'content-type':'text/event-stream'}, content=b'a'*90), max_bytes=32) is None


def test_timeout_on_idle_stream_is_bounded():
    class Slow(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.sleep(.2)
            yield b'data: too late\n\n'
    assert run(lambda req: httpx.Response(200, headers={'content-type':'text/event-stream'}, stream=Slow()),timeout_seconds=.04) is None


def test_split_sse_event_across_chunks():
    class Split(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"id":'
            yield b' 4}\n\nignored'
    result=run(lambda req: httpx.Response(200, headers={'content-type':'text/event-stream'}, stream=Split()))
    assert result.body == b'data: {"id": 4}\n\n'

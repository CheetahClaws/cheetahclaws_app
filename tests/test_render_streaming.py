import pytest
import ui.render as render


class _FakeLive:
    def __init__(self, *args, **kwargs):
        self.started = False
        self.stopped = False
        self.updates = []

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def update(self, value, refresh=False):
        self.updates.append((value, refresh))


class _FakeConsole:
    height = 100
    options = object()

    def __init__(self):
        self.printed = []

    def print(self, value):
        self.printed.append(value)


@pytest.fixture
def patched_render(monkeypatch):
    previous_state = (
        list(render._accumulated_text),
        render._current_live,
        render._plain_streaming_response,
    )
    fake_console = _FakeConsole()
    live_instances = []

    def fake_live(*args, **kwargs):
        live = _FakeLive(*args, **kwargs)
        live_instances.append(live)
        return live

    monkeypatch.setattr(render, "_RICH", True)
    monkeypatch.setattr(render, "_RICH_LIVE", True)
    monkeypatch.setattr(render, "console", fake_console)
    monkeypatch.setattr(render, "Live", fake_live)
    monkeypatch.setattr(render, "_make_renderable", lambda text: text)
    monkeypatch.setattr(render, "_live_line_limit", lambda: 80)

    render._accumulated_text.clear()
    render._current_live = None
    render._plain_streaming_response = False

    yield fake_console, live_instances

    render._accumulated_text[:] = previous_state[0]
    render._current_live = previous_state[1]
    render._plain_streaming_response = previous_state[2]


def test_stream_text_uses_one_live_renderer_with_accumulated_chunks(patched_render, monkeypatch, capsys):
    fake_console, live_instances = patched_render
    monkeypatch.setattr(render, "_rendered_line_count", lambda _: 10)

    render.stream_text("first")
    render.stream_text(" second")

    assert capsys.readouterr().out == ""
    assert fake_console.printed == []
    assert len(live_instances) == 1
    live = live_instances[0]
    assert live.started is True
    assert live.stopped is False
    assert live.updates == [("first", True), ("first second", True)]
    assert render._accumulated_text == ["first", " second"]
    assert render._plain_streaming_response is False

    render.flush_response()

    assert live.stopped is True
    assert render._accumulated_text == []
    assert render._current_live is None
    assert render._plain_streaming_response is False


def test_stream_text_falls_back_to_plain_when_first_chunk_exceeds_live_limit(
    patched_render, monkeypatch, capsys
):
    fake_console, live_instances = patched_render
    monkeypatch.setattr(render, "_rendered_line_count", lambda _: 81)

    render.stream_text("first")
    render.stream_text(" second")

    assert live_instances == []
    assert fake_console.printed == ["first"]
    assert capsys.readouterr().out == " second"
    assert render._accumulated_text == []
    assert render._current_live is None
    assert render._plain_streaming_response is True

    render.flush_response()

    assert capsys.readouterr().out == "\n"
    assert render._plain_streaming_response is False

    monkeypatch.setattr(render, "_rendered_line_count", lambda _: 10)
    render.stream_text("short")

    assert len(live_instances) == 1
    assert live_instances[0].updates == [("short", True)]
    assert render._plain_streaming_response is False


def test_stream_text_stops_active_live_before_falling_back_to_plain(patched_render, monkeypatch):
    fake_console, live_instances = patched_render
    rendered_counts = iter([10, 81])

    monkeypatch.setattr(
        render,
        "_rendered_line_count",
        lambda _renderable: next(rendered_counts),
    )

    render.stream_text("first")
    render.stream_text(" second")

    assert len(live_instances) == 1
    live = live_instances[0]
    assert live.started is True
    assert live.stopped is True
    assert live.updates == [("first", True), ("", True)]
    assert fake_console.printed == ["first second"]
    assert render._accumulated_text == []
    assert render._current_live is None
    assert render._plain_streaming_response is True

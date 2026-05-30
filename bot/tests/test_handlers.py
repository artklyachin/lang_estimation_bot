import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("GEN_API_TOKEN", "test-token")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from handlers import _speech_rate, _filler_word_count, _long_pauses, _sanitize_gpt_html, compute_metrics, analyze_fillers_gpt, handle_audio

WORDS = [
    {"text": "Hello,",    "start": 0.839, "end": 1.179, "type": "word"},
    {"text": " ",         "start": 1.179, "end": 1.359, "type": "spacing"},
    {"text": "um",        "start": 1.36,  "end": 1.48,  "type": "word"},
    {"text": " ",         "start": 1.48,  "end": 1.539, "type": "spacing"},
    {"text": "how",       "start": 1.54,  "end": 1.72,  "type": "word"},
    {"text": " ",         "start": 1.72,  "end": 1.759, "type": "spacing"},
    {"text": "like",      "start": 1.76,  "end": 1.92,  "type": "word"},
    {"text": " ",         "start": 1.92,  "end": 1.959, "type": "spacing"},
    {"text": "basically", "start": 1.96,  "end": 2.38,  "type": "word"},
    {"text": " ",         "start": 2.38,  "end": 2.419, "type": "spacing"},
    {"text": "are",       "start": 2.42,  "end": 2.58,  "type": "word"},
    {"text": " ",         "start": 2.58,  "end": 2.619, "type": "spacing"},
    {"text": "you?",      "start": 2.62,  "end": 2.879, "type": "word"},
]

RESPONSE = {"text": "Hello, um how like basically are you?", "words": WORDS}


def test_speech_rate():
    rate = _speech_rate(WORDS)
    only_words = [w for w in WORDS if w["type"] == "word"]
    expected = len(only_words) / ((only_words[-1]["end"] - only_words[0]["start"]) / 60)
    assert abs(rate - expected) < 0.01


def test_speech_rate_ignores_spacing():
    only_words = [w for w in WORDS if w["type"] == "word"]
    assert _speech_rate(WORDS) == _speech_rate(only_words)


def test_speech_rate_too_few_words():
    assert _speech_rate([WORDS[0]]) == 0.0
    assert _speech_rate([]) == 0.0


def test_filler_word_count_found():
    filler_words = ["um", "like", "basically"]
    counts = _filler_word_count(RESPONSE["text"], filler_words)
    assert counts["total"] > 0
    assert "like" in counts["breakdown"]
    assert "um" in counts["breakdown"]
    assert "basically" in counts["breakdown"]


def test_filler_word_count_none():
    counts = _filler_word_count("Hello, how are you?", ["um", "like"])
    assert counts["total"] == 0
    assert counts["breakdown"] == {}


def test_filler_word_count_empty_list():
    counts = _filler_word_count("Hello, um like basically", [])
    assert counts["total"] == 0
    assert counts["breakdown"] == {}


def test_sanitize_gpt_html_allows_bold():
    assert _sanitize_gpt_html("Hello <b>um</b> world") == "Hello <b>um</b> world"


def test_sanitize_gpt_html_strips_other_tags():
    assert _sanitize_gpt_html("<p>Hello <b>um</b></p>") == "Hello <b>um</b>"
    assert _sanitize_gpt_html("<script>evil()</script>") == "evil()"


def test_long_pauses_none():
    result = _long_pauses(WORDS, min_duration=0.7)
    assert result["per_minute"] == 0.0
    assert result["avg_duration"] == 0.0


def test_long_pauses_detected():
    words_with_pause = [
        {"text": "Hello", "start": 0.0, "end": 0.5, "type": "word"},
        {"text": "world", "start": 2.0, "end": 2.5, "type": "word"},
        {"text": "again", "start": 3.0, "end": 3.5, "type": "word"},
    ]
    result = _long_pauses(words_with_pause, min_duration=0.7)
    assert result["per_minute"] > 0
    assert result["avg_duration"] == 1.5


def test_compute_metrics_keys():
    m = compute_metrics(RESPONSE, ["um", "like", "basically"])
    assert "speech_rate_wpm" in m
    assert "filler_words" in m
    assert "filler_words_per_minute" in m
    assert "long_pauses" in m


@pytest.mark.asyncio
async def test_handle_audio_sends_report():
    def make_resp(json_data):
        r = AsyncMock()
        r.__aenter__ = AsyncMock(return_value=r)
        r.__aexit__ = AsyncMock(return_value=False)
        r.raise_for_status = MagicMock()
        r.json = AsyncMock(return_value=json_data)
        return r

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    gpt_resp = {"response": [{"message": {"content": '{"filler_words": ["um", "like", "basically"], "highlighted_text": "Hello, <b>um</b> how <b>like</b> <b>basically</b> are you?"}'}}]}
    session.post = MagicMock(side_effect=[
        make_resp({"data": {"url": "https://tmpfiles.org/1/a.ogg"}}),
        make_resp({"response": RESPONSE}),
        make_resp(gpt_resp),
    ])

    message = AsyncMock()
    message.voice = MagicMock(file_id="fid", duration=30)
    message.audio = None

    bot = AsyncMock()
    bot.get_file = AsyncMock(return_value=MagicMock(file_path="voice/f.ogg"))
    bot.download_file = AsyncMock()

    with patch("handlers.aiohttp.ClientSession", return_value=session), \
         patch("handlers.get_daily_count", AsyncMock(return_value=0)), \
         patch("handlers.get_speech_avg", AsyncMock(return_value=None)), \
         patch("handlers.save_speech_result", AsyncMock()):
        await handle_audio(message, bot)

    last_reply = message.answer.call_args_list[-1].args[0]
    assert "Паразиты:" in last_reply
    assert "Паузы:" in last_reply

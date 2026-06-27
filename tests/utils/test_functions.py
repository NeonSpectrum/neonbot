from neonbot.utils.functions import (
    clean_youtube_url,
    format_milliseconds,
    format_seconds,
    format_uptime,
    is_youtube_url,
    md_to_text,
    remove_ansi,
    split_long_message,
)


class TestFormatSeconds:
    def test_zero(self):
        assert format_seconds(0) == '00:00'

    def test_minutes(self):
        assert format_seconds(125) == '02:05'

    def test_hours(self):
        assert format_seconds(3661) == '1:01:01'

    def test_days(self):
        result = format_seconds(86400)
        assert '1 day' in result or '24:00:00' in result or '1:00:00:00' in result


class TestFormatMilliseconds:
    def test_delegates_to_seconds(self):
        assert format_milliseconds(60000) == '01:00'

    def test_zero(self):
        assert format_milliseconds(0) == '00:00'


class TestFormatUptime:
    def test_hours_minutes_seconds(self):
        result = format_uptime(3661000)
        assert '1' in result
        assert '1' in result

    def test_minutes_only(self):
        result = format_uptime(125000)
        assert '2' in result
        assert '5' in result


class TestSplitLongMessage:
    def test_short_text(self):
        result = split_long_message('hello')
        assert result == ['hello']

    def test_exact_2000(self):
        text = 'a' * 2000
        result = split_long_message(text)
        assert len(result) <= 2

    def test_long_text_splits(self):
        text = 'line1\n' + 'a' * 1995 + '\nline3'
        result = split_long_message(text)
        assert len(result) >= 2


class TestMdToText:
    def test_basic_markdown(self):
        result = md_to_text('**bold** and *italic*')
        assert 'bold' in result
        assert 'italic' in result

    def test_headers(self):
        result = md_to_text('# Header')
        assert 'Header' in result


class TestRemoveAnsi:
    def test_strips_ansi(self):
        text = '\x1b[31mred text\x1b[0m'
        result = remove_ansi(text)
        assert result == 'red text'

    def test_no_ansi(self):
        text = 'plain text'
        result = remove_ansi(text)
        assert result == 'plain text'


class TestIsYoutubeUrl:
    def test_standard(self):
        assert is_youtube_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ') is True

    def test_short(self):
        assert is_youtube_url('https://youtu.be/dQw4w9WgXcQ') is True

    def test_mobile(self):
        assert is_youtube_url('https://m.youtube.com/watch?v=dQw4w9WgXcQ') is True

    def test_non_youtube(self):
        assert is_youtube_url('https://google.com') is False

    def test_http(self):
        assert is_youtube_url('http://youtube.com/watch?v=abc') is True


class TestCleanYoutubeUrl:
    def test_removes_list_param(self):
        url = 'https://www.youtube.com/watch?v=abc123&list=PLxyz'
        result = clean_youtube_url(url)
        assert 'list=' not in result
        assert 'abc123' in result

    def test_preserves_no_list(self):
        url = 'https://www.youtube.com/watch?v=abc123'
        result = clean_youtube_url(url)
        assert result == url

    def test_short_url(self):
        url = 'https://youtu.be/abc123'
        result = clean_youtube_url(url)
        assert 'abc123' in result

from dropbox_link_generate.services.dropbox_client import _to_raw_url


def test_to_raw_url_appends_when_no_query():
    url = "https://www.dropbox.com/s/abc/file.txt"
    assert _to_raw_url(url).endswith("?raw=1")


def test_to_raw_url_overrides_dl():
    url = "https://www.dropbox.com/s/abc/file.txt?dl=0"
    out = _to_raw_url(url)
    assert "dl=0" not in out and "raw=1" in out


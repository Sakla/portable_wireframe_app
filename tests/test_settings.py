from wireframe_studio.settings import DEFAULT_PROMPT, Settings


def test_defaults_when_file_missing(tmp_path):
    s = Settings.load(tmp_path / "nope.json")
    assert s.threshold == 200 and s.default_prompt == DEFAULT_PROMPT


def test_defaults_when_file_corrupt(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text("{not json")
    assert Settings.load(p) == Settings()


def test_roundtrip_ignores_unknown_keys(tmp_path):
    p = tmp_path / "settings.json"
    s = Settings(gemini_api_key="k", line_weight=3, four_options=True)
    s.save(p)
    p.write_text(p.read_text().replace('"k"', '"k", "future_option": 1'))
    assert Settings.load(p) == s

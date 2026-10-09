import types
from pathlib import Path

import numpy as np
import onnx
import pytest
from onnx import TensorProto, helper
from PIL import Image

from wireframe_studio.engines.base import EngineError, resize_for_model
from wireframe_studio.engines.classic import ClassicEngine
from wireframe_studio.engines.dexined import DexinedEngine
from wireframe_studio.engines.gemini import GeminiEngine
from wireframe_studio.engines.lineart import LineartEngine
from wireframe_studio.engines.registry import FOUR_OPTIONS, build_engines
from wireframe_studio.settings import Settings

REPO_MODELS = Path(__file__).resolve().parents[1] / "models"


def _gray_model(path):
    """Fake line-art model: output = mean over RGB channels."""
    node = helper.make_node("ReduceMean", ["input", "axes"], ["output"], keepdims=1)
    axes = helper.make_tensor("axes", TensorProto.INT64, [1], [1])
    graph = helper.make_graph(
        [node], "g",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, None, None])],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 1, None, None])],
        [axes],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 18)])
    model.ir_version = 9
    onnx.save(model, path)


def _test_image():
    rgb = np.full((90, 130, 3), 255, np.uint8)
    rgb[30:60, 40:90] = 0
    return rgb


def test_resize_for_model_aligns_and_scales_short_side():
    out = resize_for_model(np.zeros((90, 130, 3), np.uint8), 512, 64)
    assert out.shape[0] % 64 == 0 and out.shape[1] % 64 == 0
    assert out.shape[0] == 512


@pytest.mark.parametrize("signed,align", [(False, 64), (True, 256)])
def test_lineart_engine_pre_and_post_processing(tmp_path, signed, align):
    path = tmp_path / "m.onnx"
    _gray_model(path)
    engine = LineartEngine("x", "X", path, align=align, signed=signed)
    out = engine.run(_test_image())
    assert out.shape == (90, 130) and out.dtype == np.uint8
    assert out[5, 5] > 240 and out[45, 65] < 15


def test_lineart_engine_unavailable_without_model(tmp_path):
    engine = LineartEngine("x", "X", tmp_path / "missing.onnx")
    assert not engine.available()
    with pytest.raises(EngineError):
        engine.run(_test_image())


def test_classic_engine_draws_dark_edges_on_white():
    out = ClassicEngine().run(_test_image())
    assert out.shape == (90, 130)
    assert out[5, 5] == 255
    assert out[29:32, 40:90].min() < 128  # edge of the square


@pytest.mark.skipif(not (REPO_MODELS / "dexined.onnx").is_file(), reason="run tools/fetch_models.py")
def test_dexined_engine_real_model():
    out = DexinedEngine(REPO_MODELS / "dexined.onnx").run(_test_image(), variation=1)
    assert out.shape == (90, 130)
    assert out[5, 5] > 200 and out[27:33, 60].min() < 200  # below the default black threshold


def test_registry_lists_engines_and_four_options(tmp_path):
    engines = build_engines(tmp_path, Settings)
    assert set(FOUR_OPTIONS) <= set(engines)
    assert {"classic", "gemini"} <= set(engines)
    assert engines["classic"].available()
    assert not engines["lineart_realistic"].available()


# --- Gemini ---------------------------------------------------------------

class _FakeModels:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def generate_content(self, model, contents, config):
        self.calls.append((model, contents))
        if self.error:
            raise self.error
        return self.response


def _response_with_image(size):
    import io

    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    part = types.SimpleNamespace(inline_data=types.SimpleNamespace(data=buf.getvalue()), text=None)
    return types.SimpleNamespace(candidates=[types.SimpleNamespace(content=types.SimpleNamespace(parts=[part]))])


def _gemini(models, key="key"):
    settings = Settings(gemini_api_key=key, gemini_model="m1")
    return GeminiEngine(lambda: settings, client_factory=lambda k: types.SimpleNamespace(models=models))


def test_gemini_sends_card_prompt_and_resizes_result():
    models = _FakeModels(response=_response_with_image((64, 64)))
    out = _gemini(models).run(_test_image(), prompt="draw it")
    assert out.shape == (90, 130) and out[0, 0] == 255
    model, contents = models.calls[0]
    assert model == "m1" and contents[0] == "draw it"


def test_gemini_falls_back_to_default_prompt():
    models = _FakeModels(response=_response_with_image((10, 10)))
    _gemini(models).run(_test_image(), prompt="  ")
    assert models.calls[0][1][0] == Settings().default_prompt


def test_gemini_without_key_is_unavailable():
    engine = _gemini(_FakeModels(), key="")
    assert not engine.available()
    with pytest.raises(EngineError, match="API key"):
        engine.run(_test_image())


def test_gemini_api_error_becomes_friendly_message():
    err = Exception("denied")
    err.code = 403
    with pytest.raises(EngineError, match="rejected"):
        _gemini(_FakeModels(error=err)).run(_test_image())


def test_gemini_network_error_mentions_blocked():
    with pytest.raises(EngineError, match="network blocked"):
        _gemini(_FakeModels(error=ConnectionError("refused"))).run(_test_image())


def test_gemini_text_only_response():
    part = types.SimpleNamespace(inline_data=None, text="I can't do that")
    resp = types.SimpleNamespace(candidates=[types.SimpleNamespace(content=types.SimpleNamespace(parts=[part]))])
    with pytest.raises(EngineError, match="can't do that"):
        _gemini(_FakeModels(response=resp)).run(_test_image())

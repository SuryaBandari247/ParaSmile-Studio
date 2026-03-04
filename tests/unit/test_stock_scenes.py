"""Unit tests for stock scene types and registry integration."""

from asset_orchestrator.scene_registry import SceneRegistry
from asset_orchestrator.stock_scenes import (
    StockVideoScene,
    StockWithTextScene,
    StockWithStatScene,
    StockQuoteScene,
)


class TestStockSceneRegistration:
    """Test stock scenes are registered in SceneRegistry."""

    def test_stock_video_registered(self):
        reg = SceneRegistry()
        assert reg.get("stock_video") is StockVideoScene

    def test_stock_with_text_registered(self):
        reg = SceneRegistry()
        assert reg.get("stock_with_text") is StockWithTextScene

    def test_stock_with_stat_registered(self):
        reg = SceneRegistry()
        assert reg.get("stock_with_stat") is StockWithStatScene

    def test_stock_quote_registered(self):
        reg = SceneRegistry()
        assert reg.get("stock_quote") is StockQuoteScene

    def test_all_stock_types_in_list(self):
        reg = SceneRegistry()
        types = reg.list_types()
        for t in ["stock_video", "stock_with_text", "stock_with_stat", "stock_quote"]:
            assert t in types


class TestStockSceneConstruction:
    """Test stock scene data handling."""

    def test_stock_with_text_stores_data(self):
        scene = StockWithTextScene(
            title="Test",
            data={"heading": "Hello", "body": "World", "keywords": ["test"]},
        )
        scene.construct()
        assert scene.heading == "Hello"
        assert scene.body == "World"
        assert scene.keywords == ["test"]

    def test_stock_with_stat_stores_data(self):
        scene = StockWithStatScene(
            title="Stat",
            data={"value": "$10K", "label": "TAX", "subtitle": "2026"},
        )
        scene.construct()
        assert scene.stat_value == "$10K"
        assert scene.stat_label == "TAX"

    def test_stock_quote_stores_data(self):
        scene = StockQuoteScene(
            title="Quote",
            data={"quote": "Be brave", "attribution": "Someone"},
        )
        scene.construct()
        assert scene.quote_text == "Be brave"

    def test_stock_video_default_keywords(self):
        scene = StockVideoScene(title="BG", data={})
        scene.construct()
        assert scene.keywords == []

    def test_stock_with_text_missing_keywords(self):
        scene = StockWithTextScene(title="T", data={"heading": "H"})
        scene.construct()
        assert scene.keywords == []

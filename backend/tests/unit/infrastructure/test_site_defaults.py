"""Unit tests for site_defaults helpers (deep_merge / alias normalization)."""

from __future__ import annotations

from forge.infrastructure.site_defaults import (
    DEFAULT_CONFIG,
    _normalize_aliases,
    deep_merge,
    merge_for_response,
    merge_for_save,
    sanitize_config_mojibake,
)


class TestDeepMerge:
    def test_returns_copy_not_mutation(self):
        base = {"a": 1}
        override = {"b": 2}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2}
        assert base == {"a": 1}

    def test_nested_dicts_merged_recursively(self):
        base = {"theme": {"preset": "forge", "primaryColor": "#18a058"}}
        override = {"theme": {"primaryColor": "#ff0000"}}
        result = deep_merge(base, override)
        assert result == {"theme": {"preset": "forge", "primaryColor": "#ff0000"}}

    def test_scalar_override_replaces(self):
        base = {"brand": {"name": "Forge"}}
        result = deep_merge(base, {"brand": "other"})
        assert result == {"brand": "other"}

    def test_none_override_ok(self):
        assert deep_merge({"a": 1}, None) == {"a": 1}


class TestNormalizeAliases:
    def test_feature_flags_snake_to_camel(self):
        payload = {"feature_flags": {"x": 1}}
        _normalize_aliases(payload)
        assert "featureFlags" in payload
        assert "feature_flags" not in payload
        assert payload["featureFlags"] == {"x": 1}

    def test_feature_flags_conflict_camel_wins(self):
        payload = {"feature_flags": {"x": 1}, "featureFlags": {"x": 2, "y": 3}}
        _normalize_aliases(payload)
        assert payload["featureFlags"] == {"x": 2, "y": 3}

    def test_features_alias_merged(self):
        payload = {"features": {"chat": True}}
        _normalize_aliases(payload)
        assert payload["featureFlags"] == {"chat": True}

    def test_nav_short_to_navigation(self):
        payload = {"nav": [{"key": "home"}]}
        _normalize_aliases(payload)
        assert "navigation" in payload
        assert "nav" not in payload

    def test_diy_page_slug_aliased(self):
        payload = {"diy_page_slug": "abc"}
        _normalize_aliases(payload)
        assert payload["diyPageSlug"] == "abc"

    def test_nav_items_get_defaults(self):
        payload = {"navigation": [{"key": "home"}, "not-a-dict"]}
        _normalize_aliases(payload)
        item = payload["navigation"][0]
        assert item["order"] == 0
        assert item["visible"] is True
        assert item["labelKey"] == "nav.home"
        assert item["to"] == "/"

    def test_footer_link_groups_defaults(self):
        payload = {
            "footer": {
                "linkGroups": [
                    {
                        "key": "support",
                        "links": [{"label": "Contact", "to": "/contact"}, "skip"],
                    }
                ]
            }
        }
        _normalize_aliases(payload)
        group = payload["footer"]["linkGroups"][0]
        assert group["order"] == 0
        assert group["visible"] is True
        assert group["titleKey"] == "footer.support"
        link = group["links"][0]
        assert link["order"] == 0
        assert link["visible"] is True
        assert link["labelKey"] == "footer.link"
        assert payload["footer"]["copyright"] == DEFAULT_CONFIG["footer"]["copyright"]
        assert payload["footer"]["newsletter"] is True

    def test_hero_legacy_keys_migrated(self):
        payload = {"homeHero": {"hero": {"titleKey": "home.heroTitle", "subtitleKey": "home.otherKey"}}}
        _normalize_aliases(payload)
        hero = payload["homeHero"]["hero"]
        assert hero["titleKey"] == "hero.title"
        assert hero["subtitleKey"] == "hero.otherKey"

    def test_non_dict_payload_returned_as_is(self):
        assert _normalize_aliases("x") == "x"

    def test_categories_footer_keys_canonicalised(self):
        payload = {
            "categories": [
                {"slug": "cat-food", "nameKey": "footer.petFood"},
                {"slug": "toys", "nameKey": "cat.toys"},
                {"slug": "acc", "nameKey": "accessories"},
                "not-a-dict",
            ]
        }
        _normalize_aliases(payload)
        cats = payload["categories"]
        assert cats[0]["nameKey"] == "cat.food"
        assert cats[1]["nameKey"] == "cat.toys"
        assert cats[2]["nameKey"] == "cat.accessories"
        assert cats[0]["order"] == 0
        assert cats[0]["visible"] is True
        assert cats[3] == "not-a-dict"


class TestMojibakeSanitizer:
    @staticmethod
    def _corrupt(s: str) -> str:
        """UTF-8 bytes misread as Latin-1, then stored as UTF-8 text."""
        return s.encode("utf-8").decode("latin-1")

    def test_single_round_trip_utf8_as_latin1(self):
        corrupted = self._corrupt("宠物食品")
        repaired = sanitize_config_mojibake(corrupted)
        assert repaired == "宠物食品"

    def test_normal_text_untouched(self):
        samples = [
            "宠物食品",
            "طعام الحيوانات الأليفة",
            "Zubehör",
            "Aliments pour animaux",
            "Pet Food",
            "",
        ]
        for s in samples:
            assert sanitize_config_mojibake(s) == s

    def test_recursive_dict_and_list(self):
        payload = {"nav": [{"label": self._corrupt("宠物食品")}], "i18n": {"zh": {"k": "宠物食品"}}}
        out = sanitize_config_mojibake(payload)
        assert out["nav"][0]["label"] == "宠物食品"
        assert out["i18n"]["zh"]["k"] == "宠物食品"

    def test_ascii_passthrough(self):
        assert sanitize_config_mojibake("Forge - Pet Shop") == "Forge - Pet Shop"

    def test_merge_for_save_sanitizes_payload(self):
        result = merge_for_save({"brand": {"name": self._corrupt("宠物食品")}})
        assert result["brand"]["name"] == "宠物食品"


class TestMergeForSave:
    def test_partial_payload_merged_with_defaults(self):
        result = merge_for_save({"brand": {"name": "MyShop"}})
        assert result["brand"]["name"] == "MyShop"
        assert result["brand"]["tagline"] == ""
        assert result["theme"]["preset"] == "forge"

    def test_legacy_aliases_normalized_on_save(self):
        result = merge_for_save({"feature_flags": {"chat": True}})
        assert "featureFlags" in result
        assert "feature_flags" not in result

    def test_empty_payload_returns_defaults(self):
        result = merge_for_save({})
        assert result["brand"]["name"] == "Forge"
        assert result["navigation"][0]["key"] == "home"


class TestMergeForResponse:
    def test_none_stored_returns_defaults(self):
        result = merge_for_response(None)
        assert result["brand"]["name"] == "Forge"
        assert result["theme"]["primaryColor"] == "#1C1917"

    def test_stored_override_preserved_and_missing_filled(self):
        result = merge_for_response({"brand": {"name": "Shop2"}})
        assert result["brand"]["name"] == "Shop2"
        assert result["theme"]["preset"] == "forge"
        assert result["brand"]["tagline"] == ""

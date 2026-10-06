"""Both plugin folders load into a real Tesserae app without loader errors."""


def _our_errors(registry):
    return [e for e in registry.errors if e.plugin_id in ("bin_day", "bin_day_core")]


def test_both_plugins_load_without_errors(registry):
    assert _our_errors(registry) == []
    assert registry.get("bin_day_core").kind == "data"
    assert registry.get("bin_day").kind == "widget"


def test_core_exposes_an_admin_page(client):
    resp = client.get("/plugins/bin_day_core/")
    assert resp.status_code == 200
    assert "Bin Day" in resp.get_data(as_text=True)

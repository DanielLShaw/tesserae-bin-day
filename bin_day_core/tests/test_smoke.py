"""Smoke test, in Tesserae's pattern (its docs/widgets.md, "Smoke test
pattern"). Bin Day Core has no cell, so its admin page stands in for a
render. ``client`` comes from the root conftest.py, as in bin_day's.
"""

PAGE = "/plugins/bin_day_core/"


def test_admin_page_renders(client):
    resp = client.get(PAGE)
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Bin Day Core" in body
    assert f'action="{PAGE}save"' in body


def test_a_saved_schedule_comes_back_on_the_page(client):
    form = {
        "source": "schedule",
        "schedule-0-label": "Garden waste",
        "schedule-0-first_date": "2026-10-07",
        "schedule-0-every_weeks": "2",
    }
    assert client.post(f"{PAGE}save", data=form).status_code == 302
    assert 'value="Garden waste"' in client.get(PAGE).get_data(as_text=True)

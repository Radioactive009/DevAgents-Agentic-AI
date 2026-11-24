import pytest

from app import create_app


@pytest.fixture
def client():
    with create_app().test_client() as c:
        yield c


def test_homepage_returns_200(client):
    res = client.get("/")
    assert res.status_code == 200


def test_homepage_contains_sections(client):
    html = client.get("/").data.decode("utf-8")
    for token in ("Movements Gym", '<section class="hero">', "Classes", 'id="pricing"', 'id="contact"'):
        assert token in html


def test_homepage_contains_nav_toggle_and_js(client):
    html = client.get("/").data.decode("utf-8")
    assert 'class="menu-btn"' in html
    assert 'class="menu"' in html
    assert "classList.toggle(" in html


def test_homepage_has_responsive_viewport_and_inline_styles(client):
    html = client.get("/").data.decode("utf-8")
    assert 'name="viewport"' in html
    assert "@media(min-width:768px)" in html
    assert '<style>' in html

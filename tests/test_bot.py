from types import SimpleNamespace as NS

from bgremove.bot import build_application, pick_image_file


def test_picks_largest_photo():
    small, big = NS(file_size=10), NS(file_size=999)
    got = pick_image_file(NS(photo=[small, big], document=None))
    assert got == (big, 999)


def test_picks_image_document():
    doc = NS(mime_type="image/png", file_size=5)
    assert pick_image_file(NS(photo=[], document=doc)) == (doc, 5)


def test_ignores_non_image_document():
    doc = NS(mime_type="application/pdf", file_size=5)
    assert pick_image_file(NS(photo=[], document=doc)) is None


def test_ignores_plain_text_message():
    assert pick_image_file(NS(photo=[], document=None)) is None


def test_application_builds_with_handlers():
    app = build_application("123456:TEST-TOKEN")
    assert sum(len(h) for h in app.handlers.values()) == 3

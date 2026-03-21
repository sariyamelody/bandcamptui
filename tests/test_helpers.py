"""Tests for bandcamptui helper functions."""

from unittest.mock import Mock, patch
import pytest

from bandcamptui.helpers import categorize_items, sync_selected_items


def _make_syncer(tmp_path):
    """Create a minimal mock Syncer with the public attributes helpers need."""
    syncer = Mock()
    syncer.media_format = "flac"
    syncer.bandcamp = Mock()
    syncer.bandcamp.purchases = []
    syncer.ignores = Mock()
    syncer.ignores.is_ignored = Mock(return_value=False)
    syncer.local_media = Mock()
    syncer.local_media.get_path_for_purchase = Mock(return_value=tmp_path / "Artist" / "Album")
    syncer.local_media.is_locally_downloaded = Mock(return_value=False)
    return syncer


def _make_item(**kwargs):
    """Build a mock purchase item with sane defaults."""
    defaults = dict(is_preorder=False, band_name="Artist", item_title="Album", item_id=1, folder_suffix="")
    defaults.update(kwargs)
    return Mock(**defaults)


# --- categorize_items ---

def test_categorize_items_new(tmp_path):
    syncer = _make_syncer(tmp_path)
    item = _make_item(item_id=99)
    syncer.bandcamp.purchases = [item]

    result = categorize_items(syncer)

    assert result["new"] == [item]
    assert result["downloaded"] == []
    assert result["ignored"] == []
    assert result["preorder"] == []


def test_categorize_items_preorder(tmp_path):
    syncer = _make_syncer(tmp_path)
    item = _make_item(is_preorder=True, item_id=2)
    syncer.bandcamp.purchases = [item]

    result = categorize_items(syncer)

    assert result["preorder"] == [item]
    assert result["new"] == []


def test_categorize_items_ignored(tmp_path):
    syncer = _make_syncer(tmp_path)
    item = _make_item(band_name="Skip_Me", item_id=3)
    syncer.bandcamp.purchases = [item]
    syncer.ignores.is_ignored.return_value = True

    result = categorize_items(syncer)

    assert result["ignored"] == [item]
    assert result["new"] == []


def test_categorize_items_downloaded(tmp_path):
    syncer = _make_syncer(tmp_path)
    item = _make_item(item_id=42)
    syncer.bandcamp.purchases = [item]
    syncer.local_media.is_locally_downloaded.return_value = True

    result = categorize_items(syncer)

    assert result["downloaded"] == [item]
    assert result["new"] == []


def test_categorize_items_ignored_takes_priority_over_preorder(tmp_path):
    """An item that is both ignored and a preorder lands in 'ignored', not 'preorder'."""
    syncer = _make_syncer(tmp_path)
    item = _make_item(is_preorder=True, band_name="Skip_Me", item_id=5)
    syncer.bandcamp.purchases = [item]
    syncer.ignores.is_ignored.return_value = True

    result = categorize_items(syncer)

    assert result["ignored"] == [item]
    assert result["preorder"] == []


# --- sync_selected_items ---

def test_sync_selected_items_calls_sync_item_for_each(tmp_path):
    syncer = _make_syncer(tmp_path)
    syncer.sync_item.return_value = True
    items = [_make_item(item_id=1), _make_item(item_id=2)]

    sync_selected_items(syncer, items)

    assert syncer.sync_item.call_count == 2


def test_sync_selected_items_uses_format_override(tmp_path):
    syncer = _make_syncer(tmp_path)
    syncer.sync_item.return_value = True
    item = _make_item(item_id=42)

    sync_selected_items(syncer, [item], format_overrides={42: "mp3-320"})

    syncer.sync_item.assert_called_once_with(item, encoding="mp3-320")


def test_sync_selected_items_falls_back_to_media_format(tmp_path):
    syncer = _make_syncer(tmp_path)
    syncer.sync_item.return_value = True
    item = _make_item(item_id=99)

    sync_selected_items(syncer, [item])

    syncer.sync_item.assert_called_once_with(item, encoding="flac")


def test_sync_selected_items_progress_callback_downloaded(tmp_path):
    syncer = _make_syncer(tmp_path)
    syncer.sync_item.return_value = True
    item = _make_item(item_id=1)
    callback = Mock()

    sync_selected_items(syncer, [item], progress_callback=callback)

    callback.assert_called_once_with(item, "downloaded")


def test_sync_selected_items_progress_callback_skipped(tmp_path):
    syncer = _make_syncer(tmp_path)
    syncer.sync_item.return_value = False
    item = _make_item(item_id=1)
    callback = Mock()

    sync_selected_items(syncer, [item], progress_callback=callback)

    callback.assert_called_once_with(item, "skipped")


def test_sync_selected_items_progress_callback_on_exception(tmp_path):
    syncer = _make_syncer(tmp_path)
    syncer.sync_item.side_effect = RuntimeError("boom")
    item = _make_item(item_id=1)
    callback = Mock()

    sync_selected_items(syncer, [item], progress_callback=callback)

    status = callback.call_args[0][1]
    assert status.startswith("error:")


def test_sync_selected_items_exception_does_not_abort_remaining_items(tmp_path):
    """An error on one item should not prevent the rest from being synced."""
    syncer = _make_syncer(tmp_path)
    syncer.sync_item.side_effect = [RuntimeError("fail"), True, True]
    items = [_make_item(item_id=1), _make_item(item_id=2), _make_item(item_id=3)]

    sync_selected_items(syncer, items)

    assert syncer.sync_item.call_count == 3

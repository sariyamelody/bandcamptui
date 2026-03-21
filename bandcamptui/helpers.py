def categorize_items(syncer):
    """Categorize purchases into new, downloaded, ignored, and preorder lists."""
    new_items = []
    downloaded_items = []
    ignored_items = []
    preorder_items = []
    for item in syncer.bandcamp.purchases:
        local_path = syncer.local_media.get_path_for_purchase(item)
        if syncer.ignores.is_ignored(item):
            ignored_items.append(item)
        elif item.is_preorder:
            preorder_items.append(item)
        elif syncer.local_media.is_locally_downloaded(item, local_path):
            downloaded_items.append(item)
        else:
            new_items.append(item)
    return {
        "new": new_items,
        "downloaded": downloaded_items,
        "ignored": ignored_items,
        "preorder": preorder_items,
    }


def sync_selected_items(syncer, items, format_overrides=None, progress_callback=None):
    """Sync a specific list of items with optional per-item format overrides.

    Args:
        syncer: A bandcampsync.sync.Syncer instance.
        items: List of BandcampItem objects to sync.
        format_overrides: Optional dict mapping item_id to format string.
        progress_callback: Optional callable(item, status) for progress updates.
    """
    for item in items:
        fmt = (format_overrides or {}).get(item.item_id, syncer.media_format)
        try:
            result = syncer.sync_item(item, encoding=fmt)
            if progress_callback:
                status = "downloaded" if result else "skipped"
                progress_callback(item, status)
        except Exception as e:
            if progress_callback:
                progress_callback(item, f"error: {e}")

import logging

from bandcampsync.sync import Syncer

from .app import BandcampSyncTUI, _TUILogHandler, _LOGGER_NAMES

version = "0.1.0"

__all__ = ["version", "run_interactive"]


def run_interactive(
    cookies,
    dir_path,
    media_format,
    temp_dir_root,
    ign_file_path,
    ign_patterns,
    concurrency=1,
    max_retries=3,
    retry_wait=5,
    skip_item_index=False,
    sync_ignore_file=False,
):
    syncer = Syncer(
        cookies=cookies,
        dir_path=dir_path,
        media_format=media_format,
        temp_dir_root=temp_dir_root,
        ign_file_path=ign_file_path,
        ign_patterns=ign_patterns,
        notify_url=None,
        concurrency=concurrency,
        max_retries=max_retries,
        retry_wait=retry_wait,
        skip_item_index=skip_item_index,
        sync_ignore_file=sync_ignore_file,
        auto_run=False,
    )
    app = BandcampSyncTUI(syncer)

    # Redirect all bandcampsync loggers into the TUI log pane so they don't
    # bleed through to the terminal while Textual owns the display.
    tui_handler = _TUILogHandler(app)
    saved_handlers: dict[str, list] = {}
    for name in _LOGGER_NAMES:
        logger = logging.getLogger(name)
        saved_handlers[name] = logger.handlers[:]
        logger.handlers = [tui_handler]

    try:
        app.run()
    finally:
        for name, handlers in saved_handlers.items():
            logging.getLogger(name).handlers = handlers

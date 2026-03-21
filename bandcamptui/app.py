import logging

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Header, Input, Label, OptionList, RichLog, Static
from textual import work

from bandcampsync.sync import Syncer

from .formats import AVAILABLE_FORMATS
from .helpers import categorize_items

# All bandcampsync loggers that write to stderr by default
_LOGGER_NAMES = ("sync", "notify", "media", "download", "ignores", "bandcamp")


class _TUILogHandler(logging.Handler):
    """Routes bandcampsync log records into the TUI log pane."""

    def __init__(self, app: "BandcampSyncTUI"):
        super().__init__()
        self._app = app
        self.setFormatter(logging.Formatter("%(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._app.call_from_thread(self._app._append_log, msg)
        except Exception:
            pass


SORT_FIELDS = ("artist", "title", "type")
# Column index in the DataTable for each sortable field
SORT_FIELD_COL = {"artist": 1, "title": 2, "type": 3}
COL_BASE_LABELS = (" ", "Artist", "Title", "Type", "Format", "Status")
ITEM_TYPE_MAP = {
    "a": "album",
    "t": "track",
    "p": "package",
    "s": "subscription",
}


class FormatPickerScreen(ModalScreen[str]):
    """Modal screen for picking a download format."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Cancel"),
    ]

    CSS = """
    FormatPickerScreen {
        align: center middle;
    }
    #format-picker-container {
        width: 30;
        height: auto;
        max-height: 20;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #format-picker-title {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }
    """

    def __init__(self, title="Select format", current_format="flac"):
        super().__init__()
        self.picker_title = title
        self.current_format = current_format

    def compose(self) -> ComposeResult:
        with Vertical(id="format-picker-container"):
            yield Label(self.picker_title, id="format-picker-title")
            options = []
            for fmt in AVAILABLE_FORMATS:
                label = f"  {fmt}" if fmt != self.current_format else f"> {fmt}"
                options.append(label)
            yield OptionList(*options, id="format-options")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        selected_format = AVAILABLE_FORMATS[event.option_index]
        self.dismiss(selected_format)

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)


class BandcampSyncTUI(App):
    """Interactive TUI for selecting Bandcamp albums to download."""

    TITLE = "BandcampSync Interactive"

    CSS = """
    #status-bar {
        height: 1;
        dock: top;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    #filter-bar {
        height: 3;
        dock: top;
        padding: 0 1;
        display: none;
    }
    #filter-input {
        width: 100%;
    }
    #help-bar {
        height: 1;
        dock: bottom;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    #log-pane {
        dock: bottom;
        height: 8;
        display: none;
        border-top: solid $accent;
        background: $surface;
    }
    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("space", "toggle_select", "Toggle", show=False),
        Binding("a", "select_all", "Select All", show=False),
        Binding("n", "select_none", "Select None", show=False),
        Binding("d", "download_one", "Download Now", show=False),
        Binding("f", "pick_format", "Format", show=False),
        Binding("F", "pick_global_format", "Global Format", show=False),
        Binding("s", "cycle_sort", "Sort", show=False),
        Binding("S", "reverse_sort", "Reverse Sort", show=False),
        Binding("/", "focus_filter", "Filter", show=False),
        Binding("enter", "download_selected", "Download Selected", show=False, priority=True),
        Binding("escape", "clear_filter", "Clear Filter", show=False),
        Binding("l", "toggle_log", "Toggle Log", show=False),
        Binding("g", "go_top", "Go to top", show=False),
        Binding("G", "go_bottom", "Go to bottom", show=False),
    ]

    HELP_TEXT = (
        "[b]space[/b] select  [b]a[/b] all  [b]n[/b] none  "
        "[b]enter[/b] download selected  [b]d[/b] download now  "
        "[b]s[/b] sort  [b]S[/b] reverse  [b]f[/b] format  [b]F[/b] global fmt  "
        "[b]/[/b] filter  [b]g/G[/b] top/bottom  [b]l[/b] log  [b]q[/b] quit"
    )

    def __init__(self, syncer: Syncer):
        super().__init__()
        self.syncer = syncer
        self.categories = {}
        self.all_items = []
        self.selected_ids = set()
        self.format_overrides = {}
        self.global_format = syncer.media_format
        self.sort_field_index = 0
        self.sort_reverse = False
        self.filter_text = ""
        self.item_statuses = {}  # item_id -> status string
        self._downloading = False
        self._col_keys = []
        self._log_lines: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading...", id="status-bar")
        with Horizontal(id="filter-bar"):
            yield Input(placeholder="Type to filter by artist/title...", id="filter-input")
        yield DataTable(id="items-table")
        yield RichLog(id="log-pane", highlight=False, markup=True)
        yield Static(self.HELP_TEXT, id="help-bar")

    def on_mount(self) -> None:
        table = self.query_one("#items-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        self._col_keys = list(table.add_columns(*COL_BASE_LABELS))
        table.focus()
        self.load_items()

    @work(thread=True)
    def load_items(self) -> None:
        self.categories = categorize_items(self.syncer)
        self.all_items = (
            self.categories["new"]
            + self.categories["downloaded"]
            + self.categories["preorder"]
        )
        for item in self.categories["downloaded"]:
            self.item_statuses[item.item_id] = "downloaded"
        for item in self.categories["preorder"]:
            self.item_statuses[item.item_id] = "preorder"
        self.call_from_thread(self._populate_table)

    def _populate_table(self) -> None:
        self._sort_items()
        self._refresh_table()
        self._update_column_headers()
        self._update_status_bar()

    def _update_column_headers(self) -> None:
        if not self._col_keys:
            return
        table = self.query_one("#items-table", DataTable)
        arrow = " ▼" if self.sort_reverse else " ▲"
        current = SORT_FIELDS[self.sort_field_index]
        for field, col_idx in SORT_FIELD_COL.items():
            label = COL_BASE_LABELS[col_idx] + (arrow if field == current else "")
            table.columns[self._col_keys[col_idx]].label = Text(label)
        table.refresh()

    def _get_item_type_label(self, item):
        return ITEM_TYPE_MAP.get(item.sale_item_type, getattr(item, "item_type", "?"))

    def _sort_items(self) -> None:
        field = SORT_FIELDS[self.sort_field_index]
        if field == "artist":
            key = lambda item: (item.band_name or "").lower()
        elif field == "title":
            key = lambda item: (item.item_title or "").lower()
        elif field == "type":
            key = lambda item: self._get_item_type_label(item)
        else:
            key = lambda item: (item.band_name or "").lower()
        self.all_items.sort(key=key, reverse=self.sort_reverse)

    def _filtered_items(self):
        if not self.filter_text:
            return self.all_items
        ft = self.filter_text.lower()
        return [
            item for item in self.all_items
            if ft in (item.band_name or "").lower()
            or ft in (item.item_title or "").lower()
        ]

    def _refresh_table(self) -> None:
        table = self.query_one("#items-table", DataTable)
        cursor_row = table.cursor_row
        scroll_y = table.scroll_y
        table.clear()
        for item in self._filtered_items():
            selected = "[green]●[/green]" if item.item_id in self.selected_ids else "○"
            fmt = self.format_overrides.get(item.item_id, self.global_format)
            status = self.item_statuses.get(item.item_id, "")
            type_label = self._get_item_type_label(item)
            table.add_row(
                selected,
                item.band_name or "",
                item.item_title or "",
                type_label,
                fmt,
                status,
                key=str(item.item_id),
            )
        if table.row_count > 0:
            table.move_cursor(row=min(cursor_row, table.row_count - 1), animate=False)
            table.scroll_y = scroll_y

    def _update_status_bar(self) -> None:
        count = len(self.selected_ids)
        total = len([i for i in self.all_items if not self.item_statuses.get(i.item_id)])
        sort_field = SORT_FIELDS[self.sort_field_index]
        direction = "desc" if self.sort_reverse else "asc"
        bar = self.query_one("#status-bar", Static)
        bar.update(
            f"Format: {self.global_format}  |  "
            f"Sort: {sort_field} ({direction})  |  "
            f"{count} selected  |  "
            f"{total} new  |  "
            f"{len(self.all_items)} total"
        )

    def _append_log(self, message: str) -> None:
        """Append a line to the log (call from main thread only)."""
        self._log_lines.append(message)
        self.query_one("#log-pane", RichLog).write(message)

    def _get_cursor_item(self):
        table = self.query_one("#items-table", DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except Exception:
            return None
        item_id = int(row_key.value)
        for item in self.all_items:
            if item.item_id == item_id:
                return item
        return None

    # --- Actions ---

    def check_action(self, action: str, parameters: tuple) -> bool:
        # Priority bindings (enter) must not fire when a modal screen is active
        if action == "download_selected":
            return len(self.screen_stack) == 1
        return True

    def action_toggle_select(self) -> None:
        item = self._get_cursor_item()
        if not item:
            return
        status = self.item_statuses.get(item.item_id, "")
        if status in ("downloaded", "preorder", "downloading"):
            return
        if item.item_id in self.selected_ids:
            self.selected_ids.discard(item.item_id)
        else:
            self.selected_ids.add(item.item_id)
        self._refresh_table()
        self._update_status_bar()

    def action_select_all(self) -> None:
        for item in self._filtered_items():
            status = self.item_statuses.get(item.item_id, "")
            if status not in ("downloaded", "preorder", "downloading"):
                self.selected_ids.add(item.item_id)
        self._refresh_table()
        self._update_status_bar()

    def action_select_none(self) -> None:
        self.selected_ids.clear()
        self._refresh_table()
        self._update_status_bar()

    def action_cycle_sort(self) -> None:
        self.sort_field_index = (self.sort_field_index + 1) % len(SORT_FIELDS)
        self._sort_items()
        self._refresh_table()
        self._update_column_headers()
        self._update_status_bar()

    def action_reverse_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self._sort_items()
        self._refresh_table()
        self._update_column_headers()
        self._update_status_bar()

    def action_focus_filter(self) -> None:
        filter_bar = self.query_one("#filter-bar")
        filter_input = self.query_one("#filter-input", Input)
        filter_bar.display = True
        filter_input.focus()

    def action_clear_filter(self) -> None:
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.has_focus:
            filter_input.value = ""
            self.filter_text = ""
            self.query_one("#filter-bar").display = False
            self.query_one("#items-table", DataTable).focus()
            self._refresh_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self.filter_text = event.value
            self._refresh_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-input":
            self.query_one("#filter-bar").display = False
            self.query_one("#items-table", DataTable).focus()

    def action_pick_format(self) -> None:
        item = self._get_cursor_item()
        if not item:
            return
        current = self.format_overrides.get(item.item_id, self.global_format)

        def on_format_picked(fmt: str | None) -> None:
            if fmt is not None:
                self.format_overrides[item.item_id] = fmt
                self._refresh_table()

        self.push_screen(
            FormatPickerScreen(
                title=f"Format: {item.band_name} / {item.item_title}",
                current_format=current,
            ),
            on_format_picked,
        )

    def action_pick_global_format(self) -> None:
        def on_format_picked(fmt: str | None) -> None:
            if fmt is not None:
                self.global_format = fmt
                self._refresh_table()
                self._update_status_bar()

        self.push_screen(
            FormatPickerScreen(title="Global Format", current_format=self.global_format),
            on_format_picked,
        )

    def action_go_top(self) -> None:
        self.query_one("#items-table", DataTable).move_cursor(row=0)

    def action_go_bottom(self) -> None:
        table = self.query_one("#items-table", DataTable)
        table.move_cursor(row=table.row_count - 1)

    def action_toggle_log(self) -> None:
        log_pane = self.query_one("#log-pane")
        log_pane.display = not log_pane.display

    def action_download_one(self) -> None:
        item = self._get_cursor_item()
        if not item:
            return
        status = self.item_statuses.get(item.item_id, "")
        if status in ("downloaded", "preorder", "downloading"):
            return
        self.item_statuses[item.item_id] = "downloading"
        self.selected_ids.discard(item.item_id)
        self._refresh_table()
        self._download_items_bg([item])

    def action_download_selected(self) -> None:
        if self._downloading:
            return
        items_to_download = [
            item for item in self.all_items
            if item.item_id in self.selected_ids
            and self.item_statuses.get(item.item_id, "") not in ("downloaded", "preorder", "downloading")
        ]
        if not items_to_download:
            return
        self._downloading = True
        for item in items_to_download:
            self.item_statuses[item.item_id] = "queued"
        self.selected_ids.clear()
        self._refresh_table()
        self._download_items_bg(items_to_download)

    @work(thread=True)
    def _download_items_bg(self, items) -> None:
        try:
            for item in items:
                label = f"{item.band_name} – {item.item_title}"
                self.item_statuses[item.item_id] = "downloading"
                self.call_from_thread(self._refresh_table)
                self.call_from_thread(self._append_log, f"[yellow]⬇[/yellow]  {label}")

                fmt = self.format_overrides.get(item.item_id, self.global_format)
                try:
                    result = self.syncer.sync_item(item, encoding=fmt)
                    status = "downloaded" if result else "skipped"
                    icon = "[green]✓[/green]" if result else "[dim]-[/dim]"
                    self.item_statuses[item.item_id] = status
                    self.call_from_thread(self._append_log, f"{icon}  {label}  [{fmt}]")
                except Exception as e:
                    self.item_statuses[item.item_id] = "error"
                    self.call_from_thread(self._append_log, f"[red]✗[/red]  {label}  ({e})")
                self.call_from_thread(self._refresh_table)
        finally:
            self._downloading = False
            self.call_from_thread(self._update_status_bar)

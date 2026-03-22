# bandcamptui

> **Note:** This package depends on a recent addition to bandcampsync ([PR #65](https://github.com/meeb/bandcampsync/pull/65)) that hasn't made it into a PyPI release yet. See the install instructions below.

An interactive terminal UI for selectively downloading your Bandcamp purchases. Built with [Textual](https://github.com/Textualize/textual) on top of the excellent [bandcampsync](https://github.com/meeb/bandcampsync) by [@meeb](https://github.com/meeb).

## Install

```
pip install bandcamptui
```

Until the next bandcampsync release, you'll also need to install it from source:

```
pip install git+https://github.com/meeb/bandcampsync.git
```

## Usage

```
bandcamptui -c cookies.txt -d /path/to/music
```

## Keybindings

| Key | Action |
|-----|--------|
| `space` | Toggle selection |
| `a` / `n` | Select all / none |
| `enter` | Download selected |
| `d` | Download hovered item immediately |
| `f` / `F` | Per-item / global format picker |
| `s` / `S` | Cycle sort field / reverse |
| `/` | Filter by artist or title |
| `g` / `G` | Jump to top / bottom |
| `l` | Toggle log pane |
| `q` | Quit |

## License

BSD 3-Clause, same as bandcampsync.

# bandcamptui

**GitHub:** https://github.com/sariyamelody/bandcamptui | **Docker Hub:** https://hub.docker.com/r/sariyamelody/bandcamptui

> **Note:** This package depends on a recent addition to bandcampsync ([PR #65](https://github.com/meeb/bandcampsync/pull/65)) that hasn't made it into a PyPI release yet. The Docker image already includes the correct version — if installing via pip, see the install instructions below.

An interactive terminal UI for selectively downloading your Bandcamp purchases. Built with [Textual](https://github.com/Textualize/textual) on top of the excellent [bandcampsync](https://github.com/meeb/bandcampsync) by [@meeb](https://github.com/meeb).

## Install

The recommended way to run bandcamptui is via Docker, which handles all dependencies and works on any platform:

```
docker run -it --rm \
  -v /path/to/music:/downloads \
  -v /path/to/cookies.txt:/cookies.txt:ro \
  sariyamelody/bandcamptui
```

Replace `/path/to/music` with the directory where you want downloads saved, and `/path/to/cookies.txt` with your Bandcamp cookies file.

If your terminal supports truecolor (e.g. Ghostty, iTerm2, Windows Terminal), pass `-e TERM=$TERM` to get the full theme experience:

```
docker run -it --rm \
  -e TERM=$TERM \
  -v /path/to/music:/downloads \
  -v /path/to/cookies.txt:/cookies.txt:ro \
  sariyamelody/bandcamptui
```

Additional options can be appended after the image name, e.g.:

```
docker run -it --rm \
  -v /path/to/music:/downloads \
  -v /path/to/cookies.txt:/cookies.txt:ro \
  sariyamelody/bandcamptui \
  -f mp3-v0 -j 3
```

<details>
<summary>Install from PyPI instead</summary>

```
pip install bandcamptui
```

Until the next bandcampsync release, you'll also need to install it from source:

```
pip install git+https://github.com/meeb/bandcampsync.git
```

</details>

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

# Installation

## macOS (any version supported by Mousecape)

macOS does not allow system cursors to be replaced on disk (the system volume is sealed and read-only since Big Sur). The cursors are applied at runtime with [Mousecape](https://github.com/alexzielenski/Mousecape), a free and open-source cursor manager.

1. Download and open Mousecape.
2. Double-click `macOS27-GoldenGate.cape`, or use **File → Import** in Mousecape.
3. Select *macOS 27 Golden Gate* and press **⌘↩** (Apply).
4. Optional: **Mousecape → Install Helper Tool** so the cape is re-applied after logging in.

To undo: **Mousecape → Reset to Default**.

### Some cursors stay default on Sonoma / Sequoia

Mousecape (release 1813 and current master) refuses cursors with more than 24 animation frames and then aborts the whole cape, so cursors it had not reached yet stay at the system default. The Wait cursor of macOS 27 has 30 frames. Use `macOS27-GoldenGate-Compat.cape` instead: its Wait cursor has 15 frames at the same speed, and it also defines `IBeamXOR` and `com.apple.cursor.39`, which a stock Sequoia lists but the main cape lacks. Build it with `python3 tools/build_cape_compat.py`.

Also try: **System Settings → Accessibility → Display → Pointer**: reset outline and fill colour to the defaults, **Mousecape → Reset to Default**, apply the cape again, and install the helper tool. If a cursor still does not apply, run this in Terminal to see which identifier fails:

```sh
/Applications/Mousecape.app/Contents/MacOS/mousecloak --reset
/Applications/Mousecape.app/Contents/MacOS/mousecloak --apply "$HOME/Library/Application Support/Mousecape/capes/local.macos27.goldengate.compat.cape"
```

## Windows 10 / 11

1. Extract the `macOS27-GoldenGate` folder.
2. Double-click `install.bat` and confirm the administrator prompt. It copies every cursor to `C:\Windows\Cursors\macOS27-GoldenGate`, registers the scheme for the current user, activates it and reloads the live cursor set — done.

The reload step matters: writing the registry alone (the classic `.inf` route) leaves the running session showing the old pointers until something forces a reload, so the script calls `SystemParametersInfo` with `SPI_SETCURSORS` at the end. Cursors that have no Windows role (open/closed hand, copy, alias, zoom, etc.) can be assigned manually with **Browse…** in Mouse settings.

Each `.cur`/`.ani` file contains 32, 48, 64, 96 and 128 px images, so the cursors stay sharp at any display scaling and pointer size.

To undo: choose the *Windows Default* scheme and click **Apply**.

### Larger cursors

`themes/windows/macOS27-GoldenGate-Large/` has the same cursors drawn 1.1x larger. Run its `install.bat` the same way; it installs to `C:\Windows\Cursors\macOS27-GoldenGate-Large` as the scheme *macOS 27 Golden Gate Large*, so both packages can stay installed. Static cursors include 32–256 px images; animated ones 32–128 px. Build it (or another factor) with `pip install pymupdf pillow` and `python tools/build_windows_large.py 1.1`.

Moving the pointer-size slider in *Settings → Accessibility → Mouse pointer and touch* makes Windows replace the active scheme; if that happens, select the scheme again in *Mouse settings → Pointers*.

## Linux

```sh
cd macOS27-GoldenGate
sh install.sh
```

The script copies the theme to `~/.icons/macOS27-GoldenGate` and activates it on GNOME (`gsettings`) and KDE Plasma (`plasma-apply-cursortheme`). On other desktops, select *macOS27-GoldenGate* in the cursor settings, or set it manually:

```sh
# X11 / XWayland
echo 'Xcursor.theme: macOS27-GoldenGate' >> ~/.Xresources
# Hyprland
hyprctl setcursor macOS27-GoldenGate 24
```

To install for all users, copy the folder to `/usr/share/icons/` instead. Log out and back in if some applications keep the old cursor.

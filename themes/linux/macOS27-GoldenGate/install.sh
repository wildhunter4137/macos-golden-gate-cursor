#!/bin/sh
# Install for the current user:  sh install.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.icons"
rm -rf "$HOME/.icons/macOS27-GoldenGate"
cp -a "$DIR" "$HOME/.icons/macOS27-GoldenGate"
command -v gsettings >/dev/null 2>&1 && gsettings set org.gnome.desktop.interface cursor-theme 'macOS27-GoldenGate' 2>/dev/null || true
command -v plasma-apply-cursortheme >/dev/null 2>&1 && plasma-apply-cursortheme macOS27-GoldenGate || true
echo "Installed to ~/.icons/macOS27-GoldenGate. If it did not switch automatically, select it in your cursor settings and log in again."

#!/bin/bash
cd "$(dirname "$0")/.."
while pgrep -f "codex-image.sh -o .*Krita Stencils" >/dev/null; do sleep 10; done
python3 stencils/gpt_upgrade.py photos && python3 stencils/gpt_upgrade.py faces
echo "EXIT $?"

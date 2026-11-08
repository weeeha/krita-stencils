#!/bin/bash
# Waits for the ChatGPT plan, then makes every sheet, splits them on ArtPC and builds the Krita files.
cd "$(dirname "$0")/.."
log=work/sheets_run.log
for i in $(seq 1 720); do
  python3 stencils/gpt_sheets.py test >> $log 2>&1
  [ -f work/sheets/film/a_man_40_A.png ] && break
  sleep 120
done
echo "PLAN OPEN, full run $(date)" >> $log
for k in film duos faces; do
  for try in 1 2 3; do python3 stencils/gpt_sheets.py $k >> $log 2>&1 && break; sleep 300; done
done
python3 stencils/gpt_sheets.py split >> $log 2>&1
python3 stencils/build.py film faces >> $log 2>&1
echo "ALL DONE $(date)" >> $log

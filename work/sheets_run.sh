#!/bin/bash
cd "$(dirname "$0")/.."
log=work/sheets_run.log
echo "=== full sheet run $(date)" >> $log
for k in film duos faces; do
  for try in 1 2 3; do python3 stencils/gpt_sheets.py $k >> $log 2>&1 && break; sleep 120; done
done
echo "SHEETS DONE $(date)" >> $log

#!/bin/bash
# Green change-tracking PDF: differences between the last committed manuscript
# (HEAD) and the current working tree. Additions are shown in green, deletions
# struck through in red (latexdiff defaults, additions recoloured).
# Usage: bash make_diff.sh   ->   writes/opens manuscript_diff.pdf
set -e
cd "$(dirname "$0")"
git show HEAD:manuscript.tex > /tmp/ms_old.tex
latexdiff /tmp/ms_old.tex manuscript.tex > manuscript_diff.tex 2>/dev/null
# latexdiff marks additions in blue by default -> recolour to green
sed -i '' 's/color{blue}/color{green!55!black}/g' manuscript_diff.tex
for i in 1 2 3; do
  pdflatex -interaction=nonstopmode -halt-on-error manuscript_diff.tex >/tmp/diff$i.log 2>&1 || true
  [ $i -eq 1 ] && bibtex manuscript_diff >/tmp/diffbib.log 2>&1 || true
done
if [ -f manuscript_diff.pdf ]; then
  osascript -e 'tell application "Preview" to close (every document whose name is "manuscript_diff.pdf")' 2>/dev/null || true
  open manuscript_diff.pdf
  echo "OK: manuscript_diff.pdf (green = added, red struck = removed)"
else
  echo "FAIL: siehe /tmp/diff1.log"; tail -15 /tmp/diff1.log
fi

# jd-resume-tailor config (personal; lives at ~/.config/jd-resume-tailor/config.md, never commit it)

## Resume source
- Bullet bank: ~/resume/resume.toml
- Build one variant: `cd ~/path/to/jd-resume-tailor/builder && FONT_DIR=~/fonts OUTDIR=~/resume/out uv run --with reportlab python build_resume.py ~/resume/resume.toml --variant <name>`
- (Own script instead? Describe how to add a variant and how to build, e.g. "add an entry to VARIANTS in build.py; run VARIANTS=<name> python build.py".)

## Output
- PDFs: ~/resume/out/
- Upload copies: ~/resume/out/submit_<variant>/First_Last_Resume.pdf

## Tracker (optional)
- Where to record applications (Notion database URL, spreadsheet path, Markdown table path) and which columns.

## Facts the forms keep asking
- Work authorization / sponsorship answers (truthful):
- Graduation: 
- Program availability:

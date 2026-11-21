ROLE: writer (revision {round})

You built the resume in this folder ({jobdir}) for {company} - {title}. Read ./notes.md for why you chose what you chose, and ./analysis.md.

Two reviewers read only the JD and the PDF; they never saw my bullet bank. Their reviews are below, verbatim and labelled. {checks}

How to handle them:
- Reviews are input, not orders. If one asks for an experience or skill my bank does not have, add it to "Known gaps" in analysis.md and to "gaps" in writer.json. Never invent it.
- HM "can't follow": replace jargon, add a few words of context, write it plainer. HM "doesn't believe it": state the test setup and how it was measured.
- ATS parsing and field problems: fix special characters, ligatures, links, date formats in this variant. If the problem is in the builder's template itself, report it under "questions" instead of editing the builder.
- Then rebuild, copy to ./resume.pdf, run `{check} ./resume.pdf ./analysis.md` until it passes, and update ./resume_source.md and ./notes.md.

Last, rewrite ./writer.json in the same format as before. Set "bullets_changed" to how many bullets you changed in this revision, and "touched_hard_requirement" to true if you changed a bullet that proves a hard requirement.

{reviews}

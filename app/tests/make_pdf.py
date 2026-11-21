"""Write a small text PDF without any library, for the tests (Helvetica, one link annotation)."""


def esc(s):
    return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def make_pdf(path, lines, pages=1, link='https://github.com/alexrivera-example'):
    objs = []
    kids = ' '.join(f'{3 + i * 2} 0 R' for i in range(pages))
    objs.append('<</Type/Catalog/Pages 2 0 R>>')
    objs.append(f'<</Type/Pages/Kids[{kids}]/Count {pages}>>')
    font_id = 3 + pages * 2
    annot_id = font_id + 1
    for i in range(pages):
        body = 'BT /F1 10 Tf 54 740 Td 13 TL\n' + '\n'.join(f'({esc(l)}) Tj T*' for l in lines) + '\nET'
        annots = f'/Annots[{annot_id} 0 R]' if i == 0 else ''
        objs.append(f'<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 {font_id} 0 R>>>>/Contents {4 + i * 2} 0 R{annots}>>')
        objs.append(f'<</Length {len(body)}>>\nstream\n{body}\nendstream')
    objs.append('<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>')
    objs.append(f'<</Type/Annot/Subtype/Link/Rect[54 735 300 750]/Border[0 0 0]/A<</S/URI/URI({link})>>>>')
    out = b'%PDF-1.4\n'
    offsets = []
    for n, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f'{n} 0 obj\n{o}\nendobj\n'.encode('latin-1')
    xref = len(out)
    out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode()
    for off in offsets:
        out += f'{off:010d} 00000 n \n'.encode()
    out += f'trailer\n<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF\n'.encode()
    with open(path, 'wb') as f:
        f.write(out)


RESUME_LINES = [
    'Alex Rivera', 'alex.rivera@example.com | (555) 010-2030 | Boston, MA | github.com/alexrivera-example', '',
    'EDUCATION', 'Example State University, MS in Computer Science | Sep 2026 - Dec 2027', '',
    'PROJECTS', 'Trailmap, a hiking route planner | 2026',
    '- Wrote a Dijkstra route planner in Go over 120,000 trail segments',
    '- Added pytest tests that run on every push with GitHub Actions', '',
    'EXPERIENCE', 'Software Engineering Intern, Northwind Logistics | Jun 2025 - Aug 2025',
    '- Built a Python REST API that served delivery ETAs to 3 internal teams',
    '- Cut a nightly PostgreSQL report from 14 minutes to 2 minutes by adding two indexes', '',
    'SKILLS', 'Languages: Go, Python, SQL | Tools: PostgreSQL, Docker, GitHub Actions',
] + ['- Additional true detail line for page fill'] * 34

ANALYSIS = """Company: Acme Robotics
Role: Software Engineer Intern
Level: intern (basis: Summer 2027 internship)
Direction: backend
Second direction: none (clear backend role)
Location / visa / start date: "Seattle, WA"; "We are unable to sponsor visas for this role."
Hard requirements: Python, SQL, REST APIs
Nice to have: Kubernetes, Go
ATS keywords: Python, Go, PostgreSQL, REST API/REST APIs, Kubernetes/k8s
Ideal candidate: A student who has shipped backend services.
Strategy: lead with route planning.
Known gaps:
- Kubernetes: no evidence in the bank
"""

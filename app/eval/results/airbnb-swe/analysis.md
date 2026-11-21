Company: Airbnb
Role: Software Engineering Intern (BS/MS), 2027 Summer Intern Program
Level: Intern (basis: "Less than two years of full-time, relevant work experience"; pay $7900 monthly (Bachelor's) / $8100 monthly (Master's))
Direction: backend
Second direction: ai (the JD makes "Foundational awareness of AI concepts ... model evaluation, or working with APIs backed by large language models (LLMs)" a listed requirement, and one past intern project is "search and summarize listing feedback"; backend still wins on the language/SQL requirement and the end-to-end product projects, so the two do not tie)
Location / visa / start date: "the successful applicant will need to be based in San Francisco, CA to be able to conduct their work. Interns are expected to work from the San Francisco office three days per week." / "Authorization to work in the United States is required. Please note: This role is not eligible for visa or immigration sponsorship, now or in the future." / "2027 Summer Intern Program from May 24, 2027 - August 13, 2027"; "graduating between December 2027 - June 2028"
Hard requirements: enrolled in a Bachelor's or Master's program graduating Dec 2027 - Jun 2028, less than two years of full-time relevant work experience, computer science fundamentals (data structures, algorithms, design patterns), one or more programming languages or tools (Java, Scala, Ruby/Rails, C++, SQL, HTML/CSS, JavaScript, Objective-C, Swift, Kotlin), foundational awareness of AI concepts (supervised learning, model evaluation, APIs backed by LLMs), understanding of responsible AI principles (fairness, privacy, safety), problem-solving and collaboration, clear written and verbal communication, time management and adaptability, US work authorization without sponsorship, based in San Francisco 3 days/week
Nice to have: leadership experience, teaching, mentoring, or community involvement; interest in AI/ML in products (personalized search, trust and safety); end-to-end product work (backend + user interface, as in past intern projects)
ATS keywords: Java, SQL, algorithms, data structures, design patterns, AI, LLM/LLMs/large language models, model evaluation, API/APIs, search, test, supervised learning, responsible AI, fairness, privacy, code reviews, JavaScript, HTML/CSS, Scala, Ruby/Rails, C++, Kotlin, Swift, Objective-C, mentoring/teaching/leadership
Ideal candidate: A BS/MS student graduating Dec 2027 - Jun 2028 with solid CS fundamentals who has shipped end-to-end projects in a mainstream language such as Java plus SQL. They have hands-on exposure to AI, ideally having built and evaluated something on top of LLM APIs, and they think about fairness, privacy and safety; collaboration, communication and some mentoring or community work round them out.
Strategy: Lead with Shopline (REST endpoints + PostgreSQL schema for carts/orders/inventory, tested, deployed), the closest match to past intern projects like "the backend ... for personalized Airbnb gift cards" and to the Java/SQL requirement. DocQA goes second as the AI evidence: a retrieval-augmented Q&A system that was benchmarked (12 configurations, Recall@5) and sped up, which answers "model evaluation, or working with APIs backed by large language models" and is close to the past project "search and summarize listing feedback". tinykv and throttle then show CS fundamentals (algorithms, a clean interface with swappable backends) and test/debug discipline, and the SQL internship backs up SQL. Java goes first on the Languages line, and the AI / LLM skills line sits right after Backend.
Known gaps:
- data structures: no bank bullet or coursework line names data structures (coursework lists Algorithms, Distributed Systems, Databases)
- design patterns: throttle's "4 algorithms behind one interface" is close, but the bank never names a pattern
- model evaluation: the evidence is retrieval evaluation (Recall@5 over 12 configurations) and an "LLM evaluation harnesses" skill, not evaluating an ML model
- supervised learning: no ML training or supervised-learning work in the bank
- responsible AI / fairness / privacy / safety: no bank fact about responsible AI principles
- code reviews: Shopline's CI blocks merges on failing tests, but the bank has no code review fact
- JavaScript / HTML/CSS: TypeScript is listed, but there is no frontend or UI bullet (past intern projects include user interfaces)
- Scala, Ruby/Rails, C++, Kotlin, Swift, Objective-C: no evidence; Java and SQL already cover the "one or more" requirement
- Java: only on the Languages line. Shopline uses Spring Boot and JUnit, but the bank never says "Java" in a bullet
- mentoring / teaching / leadership: nothing in the bank (nice-to-have)
- collaboration: every project in the bank is solo; no team project, open-source PR, hackathon or TA role (raised by HM review r1)
- written and verbal communication / time management / adaptability: no bank fact shows them beyond the page itself (HM r1)
- US work authorization: the bank has no authorization fact, so the header can't state it; this role requires it with no sponsorship ever (HM r1)
- held-out evaluation for DocQA: the bank reports Recall@5 on one 60-query test set and doesn't say whether the 12 configurations were chosen on a separate split (HM r1)
- measured product result for Shopline (users, load, latency): none in the bank (HM r1)
- phone number: not in the bank's profile, so the ATS phone field will be empty (ATS r1)
- project dates: only tinykv has a date (Oct 2026); Shopline, DocQA and throttle have none, and the MS start date is missing, so the Jun 2024 to MS gap can't be explained (HM + ATS r1)
- machine learning: JD intro term; no ML coursework or project in the bank (ATS r1)

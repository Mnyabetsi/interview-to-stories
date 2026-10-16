# Expected requirements: School absence reporting

Answer key for the coverage check in `eval.py`. Written from the transcript only, before looking at
any generated backlog. A Product Owner should review and edit this list. It is the "truth" the
tool is measured against.

Format: `- [ID] (kind) requirement`, where kind is requirement, nfr, open_question, scope or goal.

- [R1] (requirement) Parents can report their child's absence on their phone in about a minute, including the evening before.
- [R2] (requirement) The report captures the child, the days and a reason category (sick, doctor's appointment, family reason) without medical details.
- [R3] (requirement) Parents receive a confirmation that their report was received.
- [R4] (requirement) Parents can request planned absences in advance; up to two days the class teacher approves, longer absences the principal approves.
- [R5] (requirement) Parents can see who needs to approve a request and whether it was approved.
- [R6] (requirement) Teachers record attendance at the start of each lesson on a tablet in under a minute.
- [R7] (requirement) When a child is marked absent without a report from the parents, the school office is alerted so it can call the family.
- [R8] (requirement) Absences are visible to the class teacher, to the subject teachers who have the child that day, and as an overview to the school office.
- [R9] (requirement) The school office can enter absences reported by phone into the same system.
- [R10] (requirement) The number of absences per semester is calculated automatically for the report card.
- [R11] (requirement) Parents can be notified if their child does not arrive at school.
- [R12] (nfr) Information to parents respects custody arrangements and legal restrictions from the canton's student database.
- [R13] (nfr) Students, classes and parents come from the canton's student administration system; no manual entry.
- [R14] (nfr) Health data is protected: no free-text medical information that many people can read.
- [R15] (nfr) Available in German and English, and ideally Albanian, Portuguese and Tigrinya.
- [R16] (nfr) Report-card totals are kept; daily details are deleted after the school year (to be confirmed).
- [Q1] (open_question) Retention periods need to be confirmed with the canton's data protection officer.
- [Q2] (open_question) How does the interface to the student administration system work? (Ask the canton's IT department.)
- [G1] (goal) Success: the school knows about every missing child within 30 minutes of the first lesson.

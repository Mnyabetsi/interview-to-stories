# Expected requirements: Building permit portal

Answer key for the coverage check in `eval.py`. Written from the transcript only, before looking at
any generated backlog. A Product Owner should review and edit this list. It is the "truth" the
tool is measured against.

Format: `- [ID] (kind) requirement`, where kind is requirement, nfr, open_question, scope or goal.

- [R1] (requirement) Applicants (architects, builders and private homeowners) can submit a building permit application with all required documents online.
- [R2] (requirement) The system checks completeness before submission and prevents submitting without required documents such as the neighbour consent or signature.
- [R3] (requirement) Applicants can upload large plan PDFs (files of around 200 MB are common).
- [R4] (requirement) Applicants can see the status of their application online (received, in review, additional documents needed, decision made).
- [R5] (requirement) Internal comments, such as concerns from the fire protection office, are not visible to applicants.
- [R6] (requirement) External offices such as fire protection can review dossiers and submit their statements in the system.
- [R7] (nfr) Login with roles, including access for external authorities.
- [R8] (nfr) Every access to and change of a dossier is logged, so it can be shown in an appeal who saw and changed what.
- [R9] (nfr) Data is stored in Switzerland (requirement of the cantonal data protection office).
- [R10] (nfr) The portal is available in German and English.
- [R11] (nfr) The portal meets the federal accessibility standard and works with screen readers.
- [R12] (requirement) The decision can be delivered electronically, but only if the applicant has agreed to electronic delivery.
- [R13] (requirement) Applicants who are not comfortable with computers are supported, e.g. counter staff digitise a paper application.
- [R14] (nfr) Retention rules: building files are kept for the life of the building; other documents such as correspondence for a period still to be confirmed (around 10 years).
- [Q1] (open_question) Will paper submissions still be accepted, and if so who digitises them? (Disagreement between the Head of Building Department and the Permit Clerk; council decision needed.)
- [Q2] (open_question) What upload performance is acceptable? "Fast" was not quantified.
- [S1] (scope) First release by next summer covers online submission and status tracking; integration with the canton comes later.
- [G1] (goal) Success: most applications arrive online, fewer completeness letters (target: half) and fewer status phone calls.

# Expected requirements: Social services appointment booking

Answer key for the coverage check in `eval.py`. Written from the (German) transcript only, before
looking at any generated backlog. A Product Owner should review and edit this list. It is the
"truth" the tool is measured against.

Format: `- [ID] (kind) requirement`, where kind is requirement, nfr, open_question, scope or goal.

- [R1] (requirement) Clients can book, reschedule and cancel appointments online.
- [R2] (requirement) Follow-up appointments can be booked online with the client's own social worker.
- [R3] (requirement) First consultations (90 minutes) are not freely bookable and must be assigned to the right specialist.
- [R4] (requirement) Clients receive an SMS reminder the day before the appointment.
- [R5] (nfr) The SMS must not reveal that it is about social services; it only contains the time and address.
- [R6] (requirement) Clients can access their appointments without a classic password or E-ID, e.g. via a link or code sent by SMS.
- [R7] (nfr) Access must be secure: a forwarded link must not let someone else see another person's appointments.
- [R8] (requirement) Social workers' availability comes from their Outlook calendar; slots that are busy in Outlook cannot be booked, with no second calendar to maintain.
- [R9] (nfr) Available in German, English, Arabic and Tigrinya, in plain language.
- [Q1] (open_question) The secure login approach needs to be clarified with the data protection advisor.
- [G1] (goal) Success: half as many missed appointments and clearly fewer phone calls to reception.

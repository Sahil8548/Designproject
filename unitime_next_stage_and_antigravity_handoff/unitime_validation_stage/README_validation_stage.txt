NEXT STAGE: REFERENCE-SOLUTION AUDIT
====================================

This package audits the selected placements marked solution=true in the official UniTime committed-solution XML. It does not train an ML model or generate a new timetable.

Checks include selected room/time option membership, room capacity vs class limit, weekly room overlaps, instructor overlaps, and potential student overlaps inferred from student-to-offering enrollment. Student overlap counts are based on shared enrollment relationships and do not fully reproduce UniTime's conflict weights or date-specific logic.

Important limitations:
- Weekly day/time overlaps are checked without fully applying each class's date bitset. Some apparent overlaps may not occur on the same calendar dates.
- Group constraints are not yet evaluated because each UniTime constraint type has its own semantics (BTB, SPREAD, SAME_STUDENTS, SAME_ROOM, etc.) and preferences must be interpreted exactly.
- Room capacity exceptions, room-sharing rules, and multi-room class semantics require additional handling.
- This reference solution is a benchmark, not an independent test set.
- Do not interpret this audit as complete UniTime validation.

Use the summary CSV first. Detailed pair-level issues are provided in separate CSV files. Any detected overlaps should be reviewed against date patterns and official constraint semantics before being counted as true violations.

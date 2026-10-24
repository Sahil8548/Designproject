UniTime dataset cleaning report
================================
Source: pu-fal07-llr.xml
Benchmark: Purdue University Fall 2007 Large Lecture Room (LLR)
XML version: 2.4
Term/year: 2007Fal / 2007

What was done
-------------
1. Parsed the source XML without modifying it.
2. Converted the XML into separate normalized CSV tables.
3. Converted numeric fields to numeric types and Boolean fields to Boolean where applicable.
4. Preserved original preference values as numeric values; did not rescale them.
5. Kept candidate placements separate from selected solution assignments.
6. Kept group constraints separate from the classes linked to those constraints.
7. Kept students separate from student-offering relationships.
8. Generated a data-quality report.

Output tables
-------------
rooms.csv: 63 rooms
classes.csv: 896 classes
candidate_room_options.csv: 14823 candidate class-room options
candidate_time_options.csv: 8601 candidate class-time options
class_instructors.csv: 611 class-instructor links
group_constraints.csv: 282 group constraints
group_constraint_classes.csv: 649 constraint-class links
students.csv: 30846 students
student_offerings.csv: 92289 student-offering links
committed_solution_assignments.csv: selected assignments extracted from committed solution
automated_solution_assignments.csv: selected assignments extracted from automated solution
data_quality_checks.csv: structural validation checks

Important limitations
---------------------
- This is structural cleaning and normalization into tables, not full semantic validation of UniTime scheduling rules.
- Original XML files are unchanged.
- No ML labels were invented.
- Selected assignments are not treated as universally correct labels.
- Preference fields were not standardized because their scoring semantics differ by field/type.
- The student-offering reference check is only a cross-reference diagnostic; offering IDs can have a different scope than class IDs.
- Do not randomly split individual classes into train/validation/test sets and claim independence: classes interact through shared rooms, students, instructors, and group constraints.
- The committed and automated solutions belong to the same benchmark instance; they are not independent datasets.

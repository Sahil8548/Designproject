CANDIDATE FEATURE ENGINEERING STAGE
===================================

Generated candidate_placement_features.csv from the cleaned UniTime tables and original XML. Each row is a class-room-time candidate from joining the room and time options within the same class.

Features include room capacity fit, room/time preferences, class department/subpart, instructor count, group-constraint counts by type, and a reference-schedule contextual proxy for overlapping classes sharing student enrollments.

Important: reference_overlapping_shared_student_classes and reference_overlapping_shared_student_count_proxy are contextual diagnostic features derived by comparing each candidate with the committed reference schedule. They are NOT valid features for a model that must operate without access to that reference schedule, and must not be used if they leak the outcome or are unavailable at inference. For a fair ML evaluation, recreate these features from each partial schedule state at prediction time.

This is feature engineering, not model training. No final ML labels or performance scores are claimed. IDs are retained for joins/audits but should be excluded from predictive features.

Quality report verifies candidate count and selected solution option membership. Date-specific overlap, full group-constraint evaluation, room-sharing rules, and a new schedule optimizer remain future work.

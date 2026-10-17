"""All scoring thresholds in one place. Documented in README -> "Scoring rules".

Change numbers here to tune the engine; the explanations shown to users are
generated from these same values, so they always stay consistent.
"""

# Weight contributed by one piece of evidence, by evidence type.
EVIDENCE_WEIGHTS: dict[str, float] = {
    "code_usage": 3.0,          # a call / pattern actually used in source code (AST or line pattern)
    "source_file": 2.0,         # a non-trivial source file written in the language
    "test": 3.0,                # a test file exercising code
    "config": 3.0,              # Dockerfile, CI workflow, tsconfig ... with real content
    "commit_history": 0.5,      # one commit by the repository owner (Git skill only)
    "code_import": 1.5,         # an import that is never observed in use
    "dependency_manifest": 1.0, # requirements.txt / package.json / pom.xml entry
    "documentation": 0.5,       # README mention
    "resume_claim": 0.0,        # resume claims NEVER add evidence weight
}

# Evidence types that count as "strong" (show real implementation work).
STRONG_TYPES = {"code_usage", "source_file", "test", "config", "commit_history"}

# A single file can contribute at most this much weight to one skill
# (stops one giant file from looking like broad experience).
PER_FILE_WEIGHT_CAP = 6.0
# Commit-history weight cap for the Git skill.
COMMIT_WEIGHT_CAP = 8.0

# ---- verification status rules ------------------------------------------
# evidence_supported : strong weight >= SUPPORTED_MIN_STRONG_WEIGHT
#                      AND distinct strong-evidence files >= skill.min_files (default 2)
#                      AND no high-severity repository trust signal
# flagged_for_review : would be evidence_supported, but a HIGH severity trust
#                      signal exists for the repository -> needs human review
# partially_supported: some repository evidence, below the supported bar
#                      (e.g. dependency/README/import only, or a single file)
# unverified         : claimed on the resume, no repository evidence at all
SUPPORTED_MIN_STRONG_WEIGHT = 6.0

# ---- evidence strength (0..1) --------------------------------------------
# strength = min(1, total_weight / STRENGTH_FULL_WEIGHT)
STRENGTH_FULL_WEIGHT = 15.0

# ---- proficiency estimate -------------------------------------------------
# Only assessed when strong evidence exists. Import/manifest-only => not assessed.
# Beginner     : default once strong evidence exists
# Intermediate : >= INTERMEDIATE_MIN_FILES strong files, OR >= INTERMEDIATE_MIN_FEATURES
#                distinct features, OR any taxonomy "intermediate" feature observed
# Advanced     : (>= ADVANCED_MIN_FILES files AND >= ADVANCED_MIN_FEATURES features)
#                OR (any "advanced" feature AND >= 3 files AND >= 5 features)
INTERMEDIATE_MIN_FILES = 3
INTERMEDIATE_MIN_FEATURES = 4
ADVANCED_MIN_FILES = 6
ADVANCED_MIN_FEATURES = 8

# ---- job matching -----------------------------------------------------------
# score = 100 * sum(weight_i * credit_i) / sum(weight_i)
REQUIRED_WEIGHT = 2.0
PREFERRED_WEIGHT = 1.0
MATCH_CREDIT: dict[str, float] = {
    "evidence_supported": 1.0,
    "flagged_for_review": 0.5,
    "partially_supported": 0.5,
    "unverified": 0.0,
    "missing": 0.0,
}

# ---- authorship guard -------------------------------------------------------
BURST_MIN_COMMITS_PER_DAY = 10     # a day with at least this many commits ...
BURST_MEDIAN_MULTIPLIER = 5        # ... and >= 5x the median active-day count is a burst
LOW_OWNER_SHARE = 0.3              # owner authored < 30% of fetched commits -> signal
BULK_IMPORT_MAX_COMMITS = 3        # <= 3 commits ...
BULK_IMPORT_MIN_FILES = 30         # ... for >= 30 source files -> "code arrived in bulk" signal

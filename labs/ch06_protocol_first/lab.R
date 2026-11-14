# Chapter 6. Protocol first.
#
#     Rscript labs/ch06_protocol_first/lab.R [OUTFILE]
#
# Before anyone looks at a result: which encounters will the score be judged on?
# This lab applies the protocol's four conditions one at a time and counts what
# each leaves, by hospital and by month. Then it describes three other cohorts a
# team might have chosen, to show what the choice changes.
#
# Reads data/ only. The same numbers come from lab.py, and the two must agree.
# Run it from the top of the repository.

args <- commandArgs(trailingOnly = TRUE)
outfile <- if (length(args) >= 1) args[1] else "results/ch06_r.csv"
ROOT <- "."
CHAPTER <- "ch06"
source(file.path(ROOT, "labs", "common.R"))

SILENT_FROM <- 20230701      # the planned window, from data/network/timeline.csv
SILENT_TO <- 20231231
NEVER_SILENT <- "F06"        # joined in 2024; scoring and alerts began together
FIRST_YEAR_TO <- 20240630
ALERT_AT <- 60
HOSPITALS <- c("F01", "F02", "F03", "F04", "F05")
SMALL_HOSPITALS <- c("F04", "F05")
MONTHS <- c("2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12")

ix <- read("data/deterioration/index_encounters.csv")
day <- as.integer(gsub("-", "", substr(ix$index_datetime, 1, 10)))
month <- substr(ix$index_datetime, 1, 7)
score <- num(ix$vdi_score)

# The protocol's four conditions, each as one TRUE or FALSE per encounter.
in_window <- day >= SILENT_FROM & day <= SILENT_TO
silent_hospital <- ix$facility_id != NEVER_SILENT
not_shown <- ix$vdi_shown == "0"
has_outcome <- ix$ehr_outcome_48h != ""

# Size, events and C-statistic of one candidate cohort, among encounters with a recorded outcome.
describe <- function(name, keep) {
  keep <- keep & has_outcome
  s <- score[keep]
  outcome <- num(ix$ehr_outcome_48h[keep])
  c_stat <- c_statistic(s, outcome)
  se <- c_statistic_se(s, outcome)
  put(sprintf("n.%s_encounters", name), length(outcome))
  put(sprintf("n.%s_events", name), sum(outcome))
  put(sprintf("stat.%s_c_statistic", name), c_stat)
  put(sprintf("stat.%s_c_statistic_low", name), c_stat - 1.96 * se)
  put(sprintf("stat.%s_c_statistic_high", name), c_stat + 1.96 * se)
}

# The flow: apply the conditions in the protocol's order and count what is left.
step1 <- in_window
step2 <- step1 & silent_hospital
step3 <- step2 & not_shown
cohort <- step3 & has_outcome
put("n.index_encounters", nrow(ix))
put("n.in_window", sum(step1))
put("n.at_silent_hospitals", sum(step2))
put("n.not_shown", sum(step3))
put("n.cohort", sum(cohort))

# What each condition would remove if it were the only one.
put("n.outside_window", sum(!in_window))
put("n.at_never_silent_hospital", sum(!silent_hospital))
put("n.shown", sum(!not_shown))
put("n.no_outcome_yet", sum(!has_outcome))

# The cohort by hospital and by month.
event <- ix$ehr_outcome_48h == "1"
put("n.cohort_events", sum(cohort & event))
for (hospital in HOSPITALS) {
  here <- cohort & ix$facility_id == hospital
  put(sprintf("n.%s_encounters", tolower(hospital)), sum(here))
  put(sprintf("n.%s_events", tolower(hospital)), sum(here & event))
}
for (m in MONTHS) {
  here <- cohort & month == m
  put(sprintf("n.m%s_encounters", gsub("-", "_", m)), sum(here))
  put(sprintf("n.m%s_events", gsub("-", "_", m)), sum(here & event))
}

# Nothing was shown, so no alert fired. How many would have, at the vendor's threshold?
put("n.cohort_alerts_fired", sum(cohort & ix$alert_fired == "1"))
put("n.cohort_at_or_above_threshold", sum(cohort & score >= ALERT_AT))

# The protocol's cohort, and three cohorts a team might have chosen instead.
first_year <- day <= FIRST_YEAR_TO
small <- ix$facility_id %in% SMALL_HOSPITALS
describe("protocol", cohort)
describe("silent_as_run", not_shown)                      # every encounter that was never shown
describe("silent_after_window", not_shown & !in_window)   # silent, but after the planned window
describe("first_year", first_year)                        # the first twelve months, shown or not
put("n.first_year_shown", sum(first_year & !not_shown))
put("n.protocol_small_hospitals", sum(cohort & small))
put("n.silent_after_window_small_hospitals", sum(not_shown & !in_window & small))
write_results(outfile)

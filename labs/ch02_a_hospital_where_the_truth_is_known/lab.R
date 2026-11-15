# Chapter 2. A hospital where the truth is known.
#
#     Rscript labs/ch02_a_hospital_where_the_truth_is_known/lab.R [OUTFILE]
#
# Before any method is tried on Tonmick Health: what kind of hospital is it? This
# lab computes the headline figures an analyst would check first in any new
# extract (who is admitted, how they pay, how long they stay, how many die), and
# derives 30-day readmission from the admission files, with the rule written down.
# The chapter sets these figures beside published ones.
#
# Reads data/ only. The same numbers come from lab.py, and the two must agree.
# Run it from the top of the repository.

args <- commandArgs(trailingOnly = TRUE)
outfile <- if (length(args) >= 1) args[1] else "results/ch02_r.csv"
ROOT <- "."
CHAPTER <- "ch02"
source(file.path(ROOT, "labs", "common.R"))

YEARS <- 2022:2026
PAYERS <- c("medicare", "medicaid", "commercial", "self_pay")
ELIGIBLE <- c("home", "home_health", "snf")       # alive, to home, home health or skilled nursing
NOT_ELIGIBLE_ALIVE <- c("hospice", "ama", "transfer")
WINTER <- c(12, 1, 2)

# The five admission files stacked: every published admission, one row each.
adm <- do.call(rbind, lapply(YEARS, function(year)
  read(sprintf("data/inpatient/admissions_%d.csv", year))))
persons <- read("data/inpatient/persons.csv")
n <- nrow(adm)
put("n.hospitals", nrow(read("data/network/facilities.csv")))
put("n.persons", nrow(persons))
put("n.admissions", n)

# The value at position ceil(share * n) in sorted order, with no interpolation.
lower_value <- function(values, share) {
  ordered <- sort(values)
  ordered[ceiling(share * length(ordered))]
}

# Who is admitted, and how they pay.
age <- num(adm$age)
put("stat.age_lower_quartile", lower_value(age, 0.25))
put("stat.age_median", median(age))
put("stat.age_upper_quartile", lower_value(age, 0.75))
sex <- persons$sex[match(adm$person_id, persons$person_id)]
put("stat.female_share", sum(sex == "f", na.rm = TRUE) / n)
for (payer in PAYERS) {
  put(sprintf("stat.%s_share", payer), sum(adm$payer == payer) / n)
}
f06 <- adm$facility_id == "F06"
put("stat.f06_medicare_share", sum(f06 & adm$payer == "medicare") / sum(f06))
put("stat.emergency_share", sum(adm$admission_type == "emergency") / n)

# Winter: admissions a day in December to February against the year's average,
# at the five hospitals that were in the network for whole years 2022 to 2025.
year <- as.integer(substr(adm$admit_datetime, 1, 4))
month <- as.integer(substr(adm$admit_datetime, 6, 7))
whole <- adm$facility_id != "F06" & year >= 2022 & year <= 2025
days <- seq(as.Date("2022-01-01"), as.Date("2025-12-31"), by = "day")
winter_days <- sum(as.integer(format(days, "%m")) %in% WINTER)
in_winter <- sum(whole & month %in% WINTER)
put("stat.winter_ratio", (in_winter / winter_days) / (sum(whole) / length(days)))

# How long they stay, and how many die.
los <- num(adm$los_days)
put("n.open_stays", sum(adm$discharge_date == ""))
put("stat.los_median", median(los[!is.na(los)]))
put("stat.los_mean", mean(los[!is.na(los)]))
deaths <- sum(adm$died_in_hospital == "1")
put("n.deaths_in_hospital", deaths)
put("stat.death_share", deaths / n)

# A missing value that is not missing at random: lactate is drawn more often in the sicker.
drawn <- adm$lactate != ""
icu <- adm$icu_at_12h == "1"
put("stat.lactate_drawn_share", mean(drawn))
put("stat.lactate_drawn_icu", mean(drawn[icu]))
put("stat.lactate_drawn_not_icu", mean(drawn[!icu]))

# Each admission with the same person's next admission, if there is one.
a <- adm[order(adm$person_id, adm$admit_datetime, method = "radix"), ]
k <- nrow(a)
same <- c(a$person_id[-1] == a$person_id[-k], FALSE)
next_admit_date <- ifelse(same, substr(c(a$admit_datetime[-1], ""), 1, 10), "")
next_planned <- ifelse(same, c(a$planned_admission[-1], ""), "")

# The rule, for discharges in 2023. A discharge counts if the patient left alive
# to home, home health or skilled nursing. It has a readmission if the same person's
# next admission starts 1 to 30 days after the discharge date and was not planned.
discharged <- as.Date(a$discharge_date, format = "%Y-%m-%d")
next_admit <- as.Date(next_admit_date, format = "%Y-%m-%d")
gap <- as.numeric(next_admit - discharged)
in_2023 <- substr(a$discharge_date, 1, 4) == "2023"
eligible <- a$disposition %in% ELIGIBLE
returned <- !is.na(gap) & gap >= 1 & gap <= 30
index <- in_2023 & eligible
readmitted <- index & returned & next_planned == "0"
planned <- index & returned & next_planned == "1"

# Readmission within 30 days, derived from the admission files: 2023 discharges.
put("n.discharges_2023", sum(in_2023))
put("n.index_2023", sum(index))
put("n.readmissions_2023", sum(readmitted))
put("n.planned_returns_2023", sum(planned))
put("stat.readmission_2023", sum(readmitted) / sum(index))
for (payer in PAYERS) {
  here <- index & a$payer == payer
  put(sprintf("n.index_2023_%s", payer), sum(here))
  put(sprintf("n.readmissions_2023_%s", payer), sum(readmitted & here))
  put(sprintf("stat.readmission_2023_%s", payer), sum(readmitted & here) / sum(here))
}

# Live discharges the rule leaves out, and how many of them came back within 30 days.
left_out <- in_2023 & a$disposition %in% NOT_ELIGIBLE_ALIVE
put("n.not_eligible_alive_2023", sum(left_out))
put("n.not_eligible_returned_2023", sum(left_out & returned))
write_results(outfile)

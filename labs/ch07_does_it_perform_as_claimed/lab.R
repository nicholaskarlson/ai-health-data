# Chapter 7. Does it perform as claimed?
#
#     Rscript labs/ch07_does_it_perform_as_claimed/lab.R [OUTFILE]
#
# The vendor's model card claims a C-statistic of 0.84. This lab measures the
# score on Tonmick's own patients during the six months when it ran silently:
# scored, but shown to nobody.
#
# Reads data/ only. The same numbers come from lab.py, and the two must agree.
# Run it from the top of the repository.

args <- commandArgs(trailingOnly = TRUE)
outfile <- if (length(args) >= 1) args[1] else "results/ch07_r.csv"
ROOT <- "."
CHAPTER <- "ch07"
source(file.path(ROOT, "labs", "common.R"))

SILENT_FROM <- 20230701
SILENT_TO <- 20231231
BANDS <- c(0, 0.01, 0.02, 0.05, 0.10, 0.20, 1)   # the vendor's predicted risk, in bands

# Index encounters at the five hospitals that ran the score silently, in the
# silent window, with a recorded outcome.
ix <- read("data/deterioration/index_encounters.csv")
day <- as.integer(gsub("-", "", substr(ix$index_datetime, 1, 10)))
keep <- day >= SILENT_FROM & day <= SILENT_TO & ix$facility_id != "F06" &
  ix$vdi_shown == "0" & ix$ehr_outcome_48h != ""
score <- num(ix$vdi_score)[keep]
outcome <- num(ix$ehr_outcome_48h)[keep]
risk_table <- read("data/deterioration/vendor_risk_table.csv")
v2 <- risk_table[risk_table$vdi_version == "2.0", ]
risk <- num(v2$vendor_risk)[match(score, num(v2$vdi_score))]

events <- sum(outcome)
put("n.encounters", length(outcome))
put("n.events", events)
put("stat.event_rate", events / length(outcome))

# Discrimination: can the score tell who will deteriorate?
c_value <- c_statistic(score, outcome)
se <- c_statistic_se(score, outcome)
put("stat.c_statistic", c_value)
put("stat.c_statistic_se", se)
put("stat.c_statistic_low", c_value - 1.96 * se)
put("stat.c_statistic_high", c_value + 1.96 * se)

# Calibration: are the vendor's predicted risks the right size here?
put("stat.mean_predicted_risk", mean(risk))
oe <- events / sum(risk)
put("stat.observed_over_expected", oe)
put("stat.observed_over_expected_low", oe * exp(-1.96 / sqrt(events)))
put("stat.observed_over_expected_high", oe * exp(1.96 / sqrt(events)))
lp <- logit(risk)
fit <- logistic(matrix(lp, ncol = 1), outcome)
put("fit.calibration_intercept", fit$coef[1])
put("fit.calibration_slope", fit$coef[2])
put("fit.calibration_slope_se", fit$se[2])
large <- logistic(NULL, outcome, offset = lp)
put("fit.calibration_in_the_large", large$coef[1])
put("fit.calibration_in_the_large_se", large$se[1])

# A calibration table: predicted against observed, in bands of predicted risk.
for (k in 1:(length(BANDS) - 1)) {
  if (k < length(BANDS) - 1) {
    band <- risk >= BANDS[k] & risk < BANDS[k + 1]
  } else {
    band <- risk >= BANDS[k]
  }
  put(sprintf("n.band%d_encounters", k), sum(band))
  put(sprintf("n.band%d_events", k), sum(outcome[band]))
  put(sprintf("stat.band%d_mean_predicted", k), mean(risk[band]))
  put(sprintf("stat.band%d_observed", k), mean(outcome[band]))
}
write_results(outfile)

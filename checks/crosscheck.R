# R side of the Python and R cross-check.
#
#     Rscript checks/crosscheck.R ROOT OUTFILE
#
# Reads the CSV files under ROOT/data and ROOT/hidden (and one JSON file, the R30
# model card) and writes OUTFILE with two columns, statistic and value, to 12
# significant digits. checks/crosscheck.py computes the same list in Python, and
# checks/compare_crosscheck.py requires the two files to agree.
#
# Names say how a value is compared:
#     rows.*  n.*   counts; must be equal
#     fit.*         fitted coefficients; may differ by 1e-6
#     stat.*        everything else; must agree to a relative 1e-8
#
# Base R only, and nothing newer than R 4.1. hidden/ is simulator truth and is
# never evidence.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  cat("usage: Rscript checks/crosscheck.R ROOT OUTFILE\n")
  quit(status = 2)
}
root <- args[1]
outfile <- args[2]

names_out <- character(0)
values_out <- character(0)

put <- function(name, value) {
  if (grepl("^(rows|n)\\.", name)) {
    text <- sprintf("%d", as.integer(round(value)))
  } else {
    text <- formatC(as.numeric(value), digits = 12, format = "g")
  }
  names_out <<- c(names_out, name)
  values_out <<- c(values_out, text)
}

# Every column as text; an empty field stays an empty string.
rd <- function(path) {
  read.csv(file.path(root, path), colClasses = "character", check.names = FALSE,
           stringsAsFactors = FALSE)
}

# Text to numbers; an empty field becomes NA.
num <- function(x) {
  out <- rep(NA_real_, length(x))
  ok <- x != ""
  out[ok] <- as.numeric(x[ok])
  out
}

# Mann-Whitney C-statistic with average ranks for ties.
c_statistic <- function(score, outcome) {
  r <- rank(score, ties.method = "average")
  n1 <- as.numeric(sum(outcome == 1))
  n0 <- as.numeric(sum(outcome == 0))
  (sum(r[outcome == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}

# Maximum-likelihood logistic regression. x holds the predictors as columns,
# without the intercept. Returns the intercept first.
logistic <- function(x, y) {
  fit <- suppressWarnings(glm.fit(cbind(1, x), y, family = binomial(),
                                  control = glm.control(epsilon = 1e-12, maxit = 100)))
  as.numeric(fit$coefficients)
}

# Cohen's kappa for two 0/1 vectors.
kappa2 <- function(a, b) {
  agree <- mean(a == b)
  chance <- mean(a) * mean(b) + (1 - mean(a)) * (1 - mean(b))
  (agree - chance) / (1 - chance)
}

# ---- row counts of every CSV in the dictionary
dictionary <- rd("DICTIONARY.csv")
files <- unique(dictionary$file)
for (path in files) {
  put(paste0("rows.", path), nrow(rd(path)))
}

# ---- inpatient
adm <- do.call(rbind, lapply(2022:2026, function(year) {
  rd(sprintf("data/inpatient/admissions_%d.csv", year))
}))
persons <- rd("data/inpatient/persons.csv")
put("stat.inpatient.mean_age", mean(num(adm$age)))
put("stat.inpatient.share_emergency", mean(adm$admission_type == "emergency"))
los <- num(adm$los_days)
put("stat.inpatient.mean_los_days", mean(los[!is.na(los)]))
put("stat.inpatient.share_died", mean(adm$died_in_hospital == "1"))
put("stat.inpatient.share_lactate_drawn", mean(adm$lactate != ""))
put("stat.persons.share_female", mean(persons$sex == "f"))

# ---- the readmission model R30
dev <- rd("data/readmission/r30_development_sample.csv")
# The model card is JSON written with a two-space indent and one key to a line,
# so its "coefficients" block can be read without a JSON package.
card_lines <- readLines(file.path(root, "data/readmission/r30_model_card.json"), warn = FALSE)
block_start <- grep("^  \"coefficients\": \\{", card_lines)[1]
block_end <- which(grepl("^  \\}", card_lines) & seq_along(card_lines) > block_start)[1]
body <- card_lines[(block_start + 1):(block_end - 1)]
card_names <- sub("^\\s*\"([^\"]+)\":.*$", "\\1", body)
card_values <- as.numeric(sub(",\\s*$", "", sub("^[^:]*:\\s*", "", body)))
names(card_values) <- card_names

y <- num(dev$readmit_30d_observed)
put("n.r30.development_rows", nrow(dev))
put("n.r30.development_events", sum(y == 1))
columns <- list()
for (name in setdiff(names(dev), c("encounter_id", "prior_admits_cat"))) {
  columns[[name]] <- num(dev[[name]])
}
columns[["prior_admits_1"]] <- as.numeric(dev$prior_admits_cat == "1")
columns[["prior_admits_2_plus"]] <- as.numeric(dev$prior_admits_cat == "2")
terms <- sort(setdiff(card_names, "intercept"), method = "radix")
beta <- logistic(do.call(cbind, columns[terms]), y)
put("fit.r30.coef.intercept", beta[1])
put("stat.r30.card.intercept", card_values[["intercept"]])
lp <- rep(card_values[["intercept"]], nrow(dev))
for (j in seq_along(terms)) {
  name <- terms[j]
  put(paste0("fit.r30.coef.", name), beta[j + 1])
  put(paste0("stat.r30.card.", name), card_values[[name]])
  lp <- lp + card_values[[name]] * columns[[name]]
}
# Rank on the linear predictor in whole millionths, so that ties do not depend on the last bit.
put("stat.r30.apparent_c", c_statistic(round(lp * 1e6), y))
put("stat.r30.mean_production_score", mean(num(rd("data/readmission/r30_scores.csv")$r30_risk)))

# ---- the vendor's score in silent mode
ix <- rd("data/deterioration/index_encounters.csv")
day <- as.integer(gsub("-", "", substr(ix$index_datetime, 1, 10)))
silent <- day >= 20230701 & day <= 20231231 & ix$facility_id != "F06" & ix$ehr_outcome_48h != ""
score <- num(ix$vdi_score)[silent]
outcome <- num(ix$ehr_outcome_48h)[silent]
risk_table <- rd("data/deterioration/vendor_risk_table.csv")
v2 <- risk_table[risk_table$vdi_version == "2.0", ]
risk <- num(v2$vendor_risk)[match(score, num(v2$vdi_score))]
put("n.vdi.silent_rows", sum(silent))
put("n.vdi.silent_events", sum(outcome == 1))
put("stat.vdi.silent_c", c_statistic(score, outcome))
put("stat.vdi.silent_alert_rate", mean(score >= 60))
put("stat.vdi.silent_observed_over_expected", sum(outcome) / sum(risk))
fit <- logistic(matrix(log(risk / (1 - risk)), ncol = 1), outcome)
put("fit.vdi.calibration_intercept", fit[1])
put("fit.vdi.calibration_slope", fit[2])
review <- rd("data/deterioration/chart_review.csv")
weight <- 1 / num(review$incl_prob)
put("stat.chart_review.weighted_event_rate", sum(weight * num(review$reviewer_outcome)) / sum(weight))
rrt <- rd("data/deterioration/rrt_log.csv")
put("stat.rrt.mean_nurse_minutes", mean(num(rrt$nurse_minutes)))
put("stat.rrt.mean_physician_minutes", mean(num(rrt$physician_minutes)))
truth <- rd("hidden/deterioration/index_truth.csv")
put("stat.hidden.risk_ratio_of_response", sum(num(truth$y1)) / sum(num(truth$y0)))

# ---- the scribe
frame <- rd("data/scribe/ai_notes_frame.csv")
errors <- rd("hidden/scribe/note_errors_truth.csv")
put("stat.scribe.share_interpreter", mean(frame$interpreter_used == "1"))
put("stat.scribe.mean_visit_minutes", mean(num(frame$visit_minutes)))
has_omission <- (num(errors$n_omission) > 0)[match(frame$note_id, errors$note_id)]
v23 <- frame$scribe_version == "2.3"
put("stat.hidden.omission_rate_v23", mean(has_omission[v23]))
sample_notes <- rd("data/scribe/audit_sample.csv")
ratings <- rd("data/scribe/audit_ratings.csv")
one <- ratings[ratings$rating_round == "1", ]
one <- one[match(sample_notes$note_id, one$note_id), ]
two <- ratings[ratings$rating_round == "2", ]
two <- two[match(sample_notes$note_id, two$note_id), ]
three <- ratings[ratings$rating_round == "3", ]
put("n.scribe.adjudicated_notes", nrow(three))
put("stat.scribe.kappa_hallucination", kappa2(num(one$hallucination), num(two$hallucination)))
put("stat.scribe.kappa_omission", kappa2(num(one$omission), num(two$omission)))
final <- num(one$omission)
at <- match(sample_notes$note_id, three$note_id)
final[!is.na(at)] <- num(three$omission)[at[!is.na(at)]]
weight <- num(sample_notes$stratum_size) / num(sample_notes$stratum_sampled)
put("stat.scribe.weighted_omission_rate", sum(weight * final) / sum(weight))
put("stat.scribe.unweighted_omission_rate", mean(final))
panel <- rd("data/scribe/clinician_weeks.csv")
weekly <- rd("hidden/economics/clinician_weeks_truth.csv")
visits <- num(panel$visits)
scribe_visits <- num(panel$scribe_visits)
put("n.scribe.panel_visits", sum(visits))
put("n.scribe.panel_scribe_visits", sum(scribe_visits))
doc <- num(panel$doc_minutes_per_visit)
put("stat.scribe.mean_doc_minutes_per_visit", mean(doc[!is.na(doc)]))
since <- num(panel$weeks_since_go_live)
steady <- !is.na(since) & since >= 7
put("stat.hidden.saving_per_scribe_visit_steady",
    sum(num(weekly$saving_per_scribe_visit)[steady] * scribe_visits[steady]) / sum(scribe_visits[steady]))
survey <- rd("data/scribe/wellbeing_survey.csv")
put("stat.scribe.survey_response_rate", mean(survey$responded == "1"))
put("stat.economics.mean_loaded_hourly_cost",
    mean(num(rd("data/economics/wage_rates.csv")$loaded_hourly_cost)))

dir.create(dirname(outfile), showWarnings = FALSE, recursive = TRUE)
con <- file(outfile, open = "wb")
writeLines(c("statistic,value", paste(names_out, values_out, sep = ",")), con, sep = "\n")
close(con)
cat(sprintf("crosscheck.R: wrote %d statistics to %s\n", length(names_out), outfile))

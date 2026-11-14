# Shared functions for the labs, R side. Base R only, and nothing newer than R 4.1.
#
# Every function here has a twin of the same name in labs/common.py, and the two
# must give the same numbers: labs/compare_results.py checks it.
#
# A lab's own script (lab.py, lab.R) reads data/ only. hidden/ is simulator truth
# and is never evidence; only a lab's answer_key.py opens it.

# A CSV from the repository, every column as text; an empty field stays "".
read <- function(path) {
  read.csv(file.path(ROOT, path), colClasses = "character", check.names = FALSE,
           stringsAsFactors = FALSE)
}

# Text to numbers; an empty field becomes NA.
num <- function(x) {
  out <- rep(NA_real_, length(x))
  ok <- x != ""
  out[ok] <- as.numeric(x[ok])
  out
}

# The chance that a patient with the outcome has a higher score than one
# without it, counting a tie as one half (Mann-Whitney).
c_statistic <- function(score, outcome) {
  r <- rank(score, ties.method = "average")
  n1 <- as.numeric(sum(outcome == 1))
  n0 <- as.numeric(sum(outcome == 0))
  (sum(r[outcome == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}

# DeLong's standard error for the C-statistic.
c_statistic_se <- function(score, outcome) {
  x1 <- score[outcome == 1]
  x0 <- score[outcome == 0]
  psi <- outer(x1, x0, ">") + 0.5 * outer(x1, x0, "==")
  v10 <- rowMeans(psi)
  v01 <- colMeans(psi)
  sqrt(var(v10) / length(x1) + var(v01) / length(x0))
}

# Maximum-likelihood logistic regression. x holds the predictors as columns,
# without the intercept; pass NULL for an intercept-only model. offset is added
# to the linear predictor with its coefficient fixed at 1. Returns a list with
# the coefficients and their standard errors, intercept first.
logistic <- function(x, y, offset = NULL) {
  n <- length(y)
  design <- if (is.null(x)) matrix(1, nrow = n, ncol = 1) else cbind(1, x)
  off <- if (is.null(offset)) rep(0, n) else offset
  fit <- suppressWarnings(glm.fit(design, y, offset = off, family = binomial(),
                                  control = glm.control(epsilon = 1e-12, maxit = 100)))
  beta <- as.numeric(fit$coefficients)
  p <- 1 / (1 + exp(-(as.numeric(design %*% beta) + off)))
  information <- t(design) %*% (design * (p * (1 - p)))
  list(coef = beta, se = sqrt(diag(solve(information))))
}

logit <- function(p) log(p / (1 - p))

# Collects a lab's numbers and writes them as statistic,value. Names say how
# Python and R are compared: n.* are counts and must be equal; fit.* are fitted
# values and may differ by 1e-6; stat.* must agree to a relative 1e-8.
results_names <- character(0)
results_values <- character(0)

put <- function(name, value) {
  kind <- sub("\\..*$", "", name)
  rest <- sub("^[^.]*\\.", "", name)
  if (kind == "n") {
    text <- sprintf("%d", as.integer(round(value)))
  } else {
    text <- formatC(as.numeric(value), digits = 12, format = "g")
  }
  results_names <<- c(results_names, paste0(kind, ".", CHAPTER, ".", rest))
  results_values <<- c(results_values, text)
}

write_results <- function(path) {
  dir.create(dirname(path), showWarnings = FALSE, recursive = TRUE)
  con <- file(path, open = "wb")
  writeLines(c("statistic,value", paste(results_names, results_values, sep = ",")), con, sep = "\n")
  close(con)
  cat(sprintf("%s (R): wrote %d statistics to %s\n", CHAPTER, length(results_names), path))
}

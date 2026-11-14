PY ?= python3
LABS := $(sort $(notdir $(wildcard labs/ch*_*)))

.PHONY: all hashes verify test labs crosscheck

# Each target also works without make: run the commands shown.

# Everything a reader can check, in order. Needs R for the last two.
all: hashes verify test labs crosscheck

# The files on disk are the frozen ones.
hashes:
	sha256sum -c --quiet SHA256SUMS
	@echo "hashes OK. A matching hash confirms file identity only."

# Rebuild the whole world from its seed in a temporary folder and compare. Changes nothing.
verify:
	$(PY) generator/verify_world.py

test:
	$(PY) -m unittest discover -s tests -v

# Run every lab in Python and in R and require the two to agree. Results go to results/.
labs:
	@for lab in $(LABS); do \
	  ch=$${lab%%_*}; \
	  $(PY) labs/$$lab/lab.py results/$${ch}_python.csv || exit 1; \
	  Rscript labs/$$lab/lab.R results/$${ch}_r.csv || exit 1; \
	  $(PY) labs/compare_results.py results/$${ch}_python.csv results/$${ch}_r.csv || exit 1; \
	done

# The world's own cross-check: 104 statistics computed in Python and in R.
crosscheck:
	$(PY) checks/crosscheck.py . results/crosscheck_python.csv
	Rscript checks/crosscheck.R . results/crosscheck_r.csv
	$(PY) checks/compare_crosscheck.py results/crosscheck_python.csv results/crosscheck_r.csv

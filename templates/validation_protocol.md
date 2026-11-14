# Validation protocol

Write this before looking at any result, date it, and do not edit it afterwards; record changes as amendments. Example entries are for the vendor's deterioration score at Tonmick Health, and the analysis they describe is `labs/ch07_does_it_perform_as_claimed`.

**Tool:** *Vendor deterioration index, version 2.0.*  **Protocol date:** ______  **Authors:** ______

## 1. Question

*In adults on general wards at our five hospitals, how well does the score at 12 hours predict deterioration within 48 hours, compared with the vendor's claim?*

## 2. Population

- **Included:** *every encounter scored between 2023-07-01 and 2023-12-31 at the five hospitals, while the score was hidden from staff.*
- **Excluded:** *encounters where the score was shown; the hospital acquired later.*
- **Why this window:** *it is the only period in which nobody could act on the score.*

## 3. Outcome

- **Definition:** *transfer to intensive care, transfer to a higher level of care, or death, within 48 hours of scoring.*
- **Source:** *the record's outcome flag.*
- **Known weaknesses:** *transfers out of small hospitals may be coded as transfers, not events.*
- **Check planned:** *a stratified chart review of 800 encounters.*

## 4. Measures, fixed in advance

| Measure | Method | Reported with |
| --- | --- | --- |
| Discrimination | C-statistic, ties counted as one half | DeLong 95% interval |
| Calibration | Observed over expected; slope and intercept on the logit of the vendor's risk; calibration-in-the-large | 95% intervals; a table in bands of predicted risk |
| At the vendor's threshold | Alert rate, positive predictive value, sensitivity | Counts beside every rate |

## 5. Groups, named in advance

*Patients recorded as Black; the two northern hospitals; Medicaid and self-pay.* For each, the same measures, the number of events, and a statement of the smallest difference the data could show.

## 6. Sample size

*About 12,000 encounters and about 440 events are available. That fixes the precision; it was not chosen. Expected half-width of the interval for the C-statistic: about 0.025.* State what cannot be concluded at this size.

## 7. What each result would mean

| Result | Reading | Action |
| --- | --- | --- |
| *C-statistic within 0.05 of the claim, calibration slope 0.8 to 1.2* | *Performs about as claimed here* | *Proceed to threshold and workload review* |
| *Discrimination holds, calibration off* | *Ranks patients well, risks are the wrong size* | *Ask the vendor to recalibrate, or recalibrate locally* |
| *Discrimination well below the claim* | *Does not transfer* | *Do not go live on this evidence* |

## 8. What this protocol cannot answer

*Whether alerts improve outcomes. Whether performance holds after go-live. Whether the outcome flag is right.* Name the later work that will.

## 9. Amendments

| Date | Change | Reason | Made before or after seeing results |
| --- | --- | --- | --- |

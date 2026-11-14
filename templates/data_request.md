# Data request

Send this to whoever holds the records. Ask for the population first and the columns second: a missing patient cannot be repaired later, a missing column sometimes can. Example entries are for the deterioration score at Tonmick Health.

## 1. Population

| Item | Request | Example |
| --- | --- | --- |
| Unit of analysis | One row per ... | Scored encounter |
| Who is in | Every ... | Adult on a general ward 12 hours after admission |
| Who is out, and why | List each exclusion | In intensive care at 12 hours; comfort care |
| Sites | Every site, named | Five hospitals; a sixth from its acquisition date |
| Dates | First and last, by which date field | Scored from 2023-07-01 to 2026-06-30 |
| Excluded rows | A count for each exclusion | So the flow of patients can be reported |

Ask for everyone who was scored, not only those with an alert or an outcome.

## 2. Columns

| Group | Columns | Why |
| --- | --- | --- |
| Keys | Encounter, person, site | To link tables and to count people, not rows |
| Timing | Admission, scoring, alert, response, outcome, and the date the outcome became known | To place each row before or after each change |
| The tool's output | Score, version, whether it was shown, whether it alerted | A score nobody saw is a different thing from one that was acted on |
| The tool's inputs, as recorded | Every value the tool used | To find the input behind a subgroup failure |
| The outcome | The flag, and how it is derived | To judge how often it is wrong |
| What happened next | Response team called, evaluation done | To separate the tool from the response to it |
| Patient groups | Age, sex, recorded race and ethnicity, payer, language need, site | Named in the protocol before any result |

## 3. Things that are not rows

- The vendor's model card and its table from score to predicted risk.
- A log of changes: laboratory methods, tool versions, go-live dates by site, acquisitions.
- The rule that produced each derived column.

## 4. Checks to run on arrival

1. Row counts by site and month. A gap is a question.
2. One row per key.
3. Every date inside the window, and in the right order.
4. The share of missing values by column, site and month.
5. The score's distribution by version.

Record the answers. They are the first table of the report.

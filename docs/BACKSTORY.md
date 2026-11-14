# Tonmick Health: backstory

**Everything here is fictional.** Tonmick Health, its hospitals, clinics, vendors, products and people do not exist. No real person, hospital, health system, town, company or product appears. Nothing here is medical advice or a finding about real patients.

Milestone 0 draft, approved by Nick on 10 November 2026. `generator/spec.py` will hold the dates and sizes; if this story and the spec ever differ, the spec wins and this file is corrected.

## The region

The Tonmick region is a mid-sized part of the United States with one metro area, Tonmick City, a ring of suburbs, a band of older towns to the south, and a thinly settled rural north of lakes and farmland. About a million people live there. The Tonmick college system, which readers of the NEKpress statistics series know from another repository, serves the same fictional region. The two worlds are neighbours and nothing more: they share no people and no data.

People in the region are insured the way people in the United States are insured. Older and disabled residents have Medicare, in its traditional form or through a Medicare Advantage plan. Lower-income residents have Medicaid. Most working-age adults have commercial coverage through an employer. Some have no coverage and pay for themselves. State law plays no part in this world.

## How the network formed

Tonmick University Medical Center has stood in the middle of Tonmick City for more than a century. It is the region's teaching hospital and its only tertiary centre, with about 450 beds, the regional trauma and stroke services, and the central laboratory.

For most of its history it worked alone. That changed in the 2010s, when small hospitals across the region found it harder to stay open. Brenmoor Community Hospital, in the eastern suburbs, joined first. Tolvane Regional Hospital, the main hospital for the southern towns, followed. Then came two critical access hospitals in the north, Northfen Hospital and Pellow Lake Hospital, each with about two dozen beds and an emergency department that is the only one for many miles. By 2018 the five hospitals, a medical group and a hospice programme were operating under one board as the Tonmick Hospital Network. The public name is Tonmick Health.

The Tonmick Medical Group runs 24 clinics: 16 in primary care and 8 in specialties, with about 130 physicians, nurse practitioners and physician assistants. Tonmick Hospice and Palliative Care looks after people at home and in nursing facilities, and has a 12-bed inpatient unit beside the university hospital.

## One record

The five hospitals arrived with four different record systems. Between 2017 and 2019 the network moved all of them, and every clinic, onto a single electronic health record called Lanternis. The move was expensive and nobody enjoyed it. It is also the reason this story can be told with data: since 2019 an admission in Northfen and an admission in Tonmick City have been recorded in the same tables, with the same fields.

One record does not mean one way of working. The critical access hospitals have fewer nurses on each shift, and some charting habits there differ from the university hospital's. A value that the record offers as a default is more likely to be accepted as it stands. The central laboratory serves the university hospital, Brenmoor and Tolvane; the two northern hospitals run their own small laboratories. And the record knows only what happens inside the network. When a patient from Pellow Lake is admitted to a hospital in the next region, Lanternis never hears about it.

## The clinical analytics team

In 2020 the network set up a clinical analytics team: a physician lead, two statisticians, three analysts and a data engineer, reporting to the Chief Quality Officer. The team builds reports, answers questions from clinical leaders, and from time to time builds a model.

Its best-known model is the 30-day readmission model, R30. In 2022 the discharge-planning service asked for a way to pick out patients likely to come back to hospital soon after going home. The team had limited time and used the data nearest to hand: medicine-service discharges from the university hospital in the first half of 2022, keeping only the patients whose laboratory panel was complete. They turned age and length of stay into yes-or-no variables, screened candidate predictors one at a time, fitted a logistic regression and reported how well it separated the patients it was built on. The number looked good. From February 2023 the R30 score appeared on the discharge-planning worklist at every hospital in the network.

Nobody checked whether the score worked as well in Tolvane or Pellow Lake as it had on paper in Tonmick City. Nobody could show that the worklist changed what happened to patients.

## The deterioration score

Every hospital fears the patient who looks stable at noon and is in intensive care by midnight. In 2023 the network licensed a commercial early-warning tool, the Venncroft Deterioration Index, known as VDI. Venncroft sells it as an add-on to Lanternis. It reads each ward patient's vital signs, a few laboratory results and some history, and returns a score from 0 to 100. The vendor's model card reports strong performance on the vendor's own multi-site data, and gives a table that turns each score into a risk of deterioration within 48 hours. How the score is calculated is the vendor's secret.

The Chief Nursing Officer and the hospitalist group wanted the tool for a plain reason: rapid-response teams were being called late. The plan was careful. From July to December 2023 the score ran in silent mode at all five hospitals: calculated and stored, but shown to nobody. Alerts went live at the university hospital, Brenmoor and Tolvane in January 2024, and at the two northern hospitals in April. An alert fires when the score reaches 60. The ward's charge nurse is paged, and in most cases the rapid-response team comes to see the patient.

The silent-mode data were collected. In the pressure of going live, they were never properly analysed.

## The acquisition

Sallowfield Memorial Hospital is a 150-bed community hospital in the south of the region. It is older than the others, its patients are older too, and a larger share of them have Medicare. After several years of losses its board agreed to join Tonmick Health. The acquisition closed on 1 October 2024, and Sallowfield's admissions have been in the network's data since that day.

Sallowfield moved onto Lanternis quickly, and the tools came with it. VDI alerts were switched on there in January 2025. There was no silent-mode period. The integration team's reasoning was that the score had been running across the network for a year and a half without trouble. That reasoning assumed Sallowfield's patients, staff and charting were like everyone else's. Nobody tested the assumption. The network's own review later called this a governance gap.

## The scribe

The Tonmick Medical Group's clinicians spend a large part of each day, and many evenings, writing notes. In 2024 the group's leaders chose an ambient AI scribe, Harkwell Ambient. With the patient's consent it listens to the visit and drafts the note. The clinician reads the draft, corrects it and signs it.

The medical group's leaders did one thing that the hospital side had not: they planned the rollout so that it could be evaluated. Measurement began on 6 January 2025, before any clinic had the tool. The 24 clinics were then assigned at random to four start dates, three months apart, from April 2025 to January 2026, with primary care and specialty clinics balanced across the four groups. Every clinic gets the scribe in the end; the order was decided by a seeded draw. Clinicians choose, visit by visit, whether to use it. Behavioural health was left out of the pilot. Its visits are long and sensitive, consent to recording is a harder question there, and the vendor had not tested the product on that kind of conversation.

A short staff survey, the Tonmick Clinician Pulse, was fielded before the rollout, three months after each clinic's start, and again at the end. The vendor replaced version 2.3 of its model with version 2.4 in November 2025.

## Hospice

The hospice programme joined these conversations late, and for its own reasons. Hospice staff are asked the same question every day by families and by the health plans: how long? For years the programme's nurses have recorded a simple measure of daily function at each visit, the Tonmick Daily Function Score. It rates mobility, self-care, eating and drinking, and alertness, and adds them to a total from 0 to 12. Admitting clinicians also write down how long they expect each patient to live. The programme has more than five years of these records and has never compared the predictions with what happened.

Hospice has a second problem that makes any such comparison tricky. Not everyone who enters hospice dies there. Some patients stabilise and are discharged, some choose to return to active treatment, and some move away. Analysts who forget this get the wrong answers.

## Things nobody announced

Health systems change all the time, and most changes are small and local. A few of the changes at Tonmick Health matter for what follows, and none of them was announced as important at the time.

In March 2024 the central laboratory changed the method it uses to measure one analyte. The change was entered in the laboratory's change log, among dozens of routine entries, as laboratories do. Over the following two years the rapid-response teams, who had answered nearly every alert at first, began to answer fewer of them. The acquisition brought a different patient population into the data. In February 2026 the vendor issued version 3.0 of VDI, describing it as a recalibration. Winter came each year and brought more admissions and sicker patients.

None of these was hidden. Each sits somewhere in the data, in the place where a real hospital would have recorded it.

## The AI Oversight Committee

By the middle of 2025 the Chief Medical Officer was hearing the same question from several directions. A nurse manager in Northfen said the alerts there seemed to miss patients. A hospitalist at the university hospital said there were more alerts than a year earlier and fewer of them meant anything. The medical group wanted to know whether the scribe's notes could be trusted. The Chief Financial Officer wanted to know whether the scribe was worth its licence fee. And in the autumn of 2025, national guidance from accreditation and industry bodies urged health systems to validate AI tools on their own patients and to keep monitoring them after go-live.

In September 2025 the board formed the AI Oversight Committee. Its members are the Chief Quality Officer, who chairs it; the Chief Medical Information Officer; a hospitalist; a primary care physician; the Chief Nursing Officer's deputy; the hospice medical director; a statistician from the clinical analytics team; a member of the compliance office; and a patient representative. The committee has no budget to buy anything. Its job is to say, with evidence, what the network's tools actually do.

In its first months it commissioned four pieces of work:

- a local validation of VDI on the 2023 silent-mode data, with a clinician chart review of 800 encounters to check how well the record captures deterioration;
- an audit of AI-drafted notes: a stratified random sample of 1,200 notes, each rated independently by two clinicians, with a senior reviewer settling disagreements;
- a value review of the scribe, using the rollout data, the survey and the costs;
- a look back at R30, which the committee had inherited without ever having approved it.

## The committee's questions

The committee wrote its questions down. They are the reason this world exists, and each one is the starting point of a book in the series.

1. **Is our readmission model any good?** R30 looked accurate on the patients it was built from. Does it rank and calibrate well on later patients, at other hospitals? Was the development sample ever large enough? What did the modelling choices cost?
2. **Does the vendor's score work on our patients?** The model card describes the vendor's population, not ours. How does VDI perform here, overall and for particular groups of patients and particular hospitals, and why? What should we have done before switching it on at Sallowfield?
3. **Can we trust the AI-drafted notes?** How often does a draft leave something out, add something that was not said, or attribute it to the wrong person? How sure can we be, given that we reviewed a sample and that reviewers disagree?
4. **How long do our hospice patients live, and can we say so honestly?** What do survival estimates look like when some patients leave alive, when hazards do not stay in proportion, and when the data simply stop on a fixed date? How far off are our clinicians' predictions?
5. **Is the deterioration score still working?** Performance was never checked after go-live. What has changed since 2024, when, and how would we have known sooner? How do we judge a score once its alerts change the outcomes it predicts?
6. **Is the scribe worth it?** Does it save clinicians time, and how much? Does it change their evenings or their wellbeing? What does it cost against what it saves, once we account for who chose to use it and for trends that were already under way?
7. **How do we practise all of this safely?** The committee wants its analysts to rehearse these methods on data where the right answer is known, before they are used on decisions that matter.

The data in this repository are what the committee's analysts were given. The right answers exist as well, in a folder the analysts never see.

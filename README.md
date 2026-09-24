# The Unofficial Guide

Ulysses Echeverria — corpus: `campus_life`

---

# Unit 1

## What This Does

This is a question-answering system over `campus_life`, a corpus of 88 short
posts in which students explain the parts of university life that nobody
documents properly — which dining hall has a twenty-minute queue at 12:15, what
a wash costs in each dorm, how many hours a week a given course really takes,
and the administrative rules (pass/fail deadlines, the housing lottery, printing
quotas) that students learn from each other rather than from the registrar.

You ask it a question in plain English. It finds the handful of posts closest in
meaning to what you asked, hands those to a language model, and gets back an
answer that names the file it came from. If nothing in the corpus is close
enough to your question, it refuses instead of guessing — ask it about diesel
engines and it will tell you it doesn't know rather than improvise from a post
about meal plan changes.

## Chunking Strategy

**Chunk size:** 600 characters — a ceiling this corpus never actually reaches
**Overlap:** 0 characters

Every document in `campus_life` has the same shape: a short title line naming
the thing, a blank line, then two or three short paragraphs.

```
Laundry in Calder Annexe

Machines take $2.00 wash, $1.75 dry, app-based. There are eight washers
and six dryers for the building, which is the wrong ratio and means the
dryers back up on Sunday evenings.

Best time to do laundry here is Tuesday or Wednesday morning. Sunday
after 6pm you will wait.
```

Two things I noticed reading these decided the whole strategy.

**The documents are tiny.** All 88 run between 178 and 549 characters, mean 317.
Not one reaches the starter's 800-character window, so `fallback_split` was
never cutting anything at all — 88 documents in, 88 chunks out. The default
wasn't working badly, it wasn't running.

**The title line is load-bearing.** It is the only place the building or course
name reliably appears. Look at the laundry document above: the second paragraph
says "the dryers back up on Sunday evenings" without ever saying *whose* dryers.
And that paragraph is not unique — it appears word-for-word in seven different
dorms' laundry files. I counted the whole corpus: 25 of 183 body paragraphs
(14%) appear verbatim in more than one document, one of them in nine.

**I changed my mind here, and the measurement is why.** My first instinct was
that documents this short and this cleanly laid out obviously wanted splitting
on blank lines — one paragraph, one idea, one chunk. I expected the failure to
be wrong attribution: seven identical "Sunday evenings" paragraphs with seven
different filenames, and no way for retrieval to tell them apart.

So I built it and measured it before committing to it. The result was 271
chunks — and **88 of them (32%) were a bare title line with no content under
it.** The shortest was 10 characters. Worse, they *win*: I probed the
paragraph-split index with eight questions and a content-free heading ranked #1
for four of them.

```
[orphan ranked #1]  "how much does a wash cost in Calder Annexe?"
                     -> chunk text: "Laundry in Calder Annexe"       (24 chars)
[orphan ranked #1]  "how noisy is Tamsin Court?"
                     -> chunk text: "Noise levels in Tamsin Court"   (28 chars)
```

Those chunks match the question almost perfectly, because a title is a pure
statement of topic. They also answer nothing whatsoever. My predicted failure
(wrong attribution) barely materialised; the failure I hadn't predicted was
worse, and I'd have shipped it if I'd trusted the reasoning instead of the
count.

So `chunker.py::split_documents` does this instead:

1. Peel the title line off the document.
2. If title + body fits under the 600-character ceiling, **the document stays
   whole**. On this corpus that is all 88 of them.
3. If it doesn't fit, pack *whole paragraphs* up to the ceiling, only ever
   splitting inside a paragraph on a sentence boundary.
4. **Staple the title line back onto every piece**, so no chunk can lose the
   name of the building or course it describes.
5. Merge anything under 100 characters into its neighbour, which makes an
   orphan chunk impossible by construction rather than by luck.

Rules 2–5 mean this corpus is never cut, which sounds like doing nothing and
isn't: the work is in rules 4 and 5, which are what stop the obvious approach
from wrecking retrieval. To check the splitting path isn't dead code I ran the
same chunker over `city_guides`, whose documents average 2,068 characters: 14
documents became 61 chunks, still 0 under the floor and still 0 missing their
title.

**Why 600 and why zero overlap.** 600 sits just above the longest document
(549), so every post stays whole, while still bounding a chunk if I add a longer
document later. Overlap is 0 because overlap exists to stop a fact being severed
at a cut point, and this strategy makes no cuts — there is nothing to sever.
Non-zero overlap would actively hurt here: duplicating text across boundaries
would add more near-identical vectors to a corpus whose central retrieval
problem is already near-identical vectors.

## Sample Chunks

From `python app.py chunks -n 5`. Every one carries its title line and reads as
a complete thought on its own — which is criterion 4, and the whole point of the
strategy above.

**Chunk 1** — source: `admin_add_drop_deadline.txt#0` — produced by: `chunker.py::split_documents`

```
On the add/drop deadline

You can add a course through the end of the second week. Dropping is a longer window — through the end of week six — but a drop after week two shows as a W on your transcript. Nothing anywhere on the registrar's site says this plainly, and students find out from each other.
```

**Chunk 2** — source: `course_biol_160.txt#0` — produced by: `chunker.py::split_documents`

```
BIOL 160 Cell Biology

I lived here my sophomore year. Format is lecture three times a week with a weekly lab. Assessment: four unit tests and a cumulative final. Not curved.

Expect 9 to 11 hours a week, the heaviest first-year course by reputation.

The one piece of advice: the unit tests come fast, roughly every three weeks; falling behind once is very hard to recover from.
```

**Chunk 3** — source: `course_hist_118_workload.txt#0` — produced by: `chunker.py::split_documents`

```
Workload for HIST 118 Modern World History

People keep asking so: a lot of reading, about 120 pages a week, but no problem sets. That's real time, not optimistic time.

It's front-loaded — the first month is heavier than the rest, partly because you're learning the format.
```

**Chunk 4** — source: `dining_pellew_dining_hall_followup.txt#0` — produced by: `chunker.py::split_documents`

```
Re: Pellew Dining Hall

Adding to what people have said about Pellew Dining Hall. The wait figure of 12 to 18 minutes at peak matches what I've seen. If you're trying to eat between classes, go before 11:45 and it's a different building entirely.

Also worth saying: the furthest hall from anywhere, next to the athletics centre. Nobody tells you this at orientation.
```

**Chunk 5** — source: `housing_innisfree_hall.txt#0` — produced by: `chunker.py::split_documents`

```
Innisfree Hall — what it's actually like

Transferred in last year, so take this with a grain of salt. Built 1991, renovated 2022. Rooms are doubles arranged as pairs sharing one bathroom between two rooms.

The good: the shared-bathroom-between-two-rooms arrangement is the best compromise on campus.

The bad: no air conditioning, which matters for the first three weeks of September.

Laundry costs $1.75 wash, $1.75 dry, app-based. On noise: moderate; the building is L-shaped and the short wing is much quieter.
```

Chunk 3 is the one that makes the case. Its second paragraph — "It's
front-loaded…" — is identical in all nine course workload files. On its own it
is unattributable. Kept under its title line it is unambiguous.

## Sample Answer

**Question:** What does a wash cost in Calder Annexe?

**Answer:** (from `python app.py ask "What does a wash cost in Calder Annexe?"`)

```
  (best distance 0.254, cutoff 0.7)

A wash costs $2.00 in Calder Annexe (housing_calder_annexe.txt and housing_calder_annexe_laundry.txt).

Sources retrieved: housing_aldridge_hall_laundry.txt, housing_calder_annexe.txt, housing_calder_annexe_laundry.txt, housing_innisfree_hall_laundry.txt, housing_old_brewhouse_laundry.txt
```

I picked this one because it's the question I most expected to fail. Three of
the five chunks retrieved are laundry posts for the *wrong* buildings — Aldridge
($1.75), Innisfree ($1.75), Old Brewhouse ($1.50) — and they're near-identical
prose to the right one. The model had four different wash prices in front of it
and picked the right one, and both files it cites genuinely contain `$2.00`.

**My relevance cutoff:** `THRESHOLD = 0.70`

| Question | In corpus? | Best distance |
|---|---|---|
| What does a wash cost in Calder Annexe? | Yes | 0.2542 |
| How late can I declare a course pass/fail, and what grade do I need to pass it? | Yes | 0.2087 |
| How often does the campus shuttle run on weekends? | Yes | 0.4114 |
| How many midterms does PHYS 130 have, and is there a final? | Yes | 0.2843 |
| How many two-hour blocks can one person book in a group study room each week? | Yes | 0.1868 |
| What is the capital of Mongolia? | No | 0.8246 |
| How do I change the oil in a diesel engine? | No | 0.9340 |
| Who won the 1994 World Cup? | No | 0.8859 |
| What is the recommended dosage of ibuprofen for a headache? | No | 0.8442 |
| How do I write a for loop in Rust? | No | 0.8960 |

In corpus: **0.187 – 0.411.** Out of corpus: **0.825 – 0.934.** A gap 0.41 wide
with nothing whatsoever inside it.

That gap is wider than I predicted. Writing criterion 3 I argued `campus_life`
is broad enough that an outside question could drift toward it on vocabulary
alone — ibuprofen toward the health centre post, Rust toward CS 210 — and that I
might have to accept one leak. Neither happened: ibuprofen landed at 0.844 (on
`money_textbooks.txt`, of all things) and Rust at 0.896. The prediction was
wrong and the criterion was more pessimistic than it needed to be.

**Why 0.70 and not the midpoint.** The midpoint of the gap is 0.618, which is
roughly the shipped default, and taking it would have been the obvious move. I
didn't, because the two groups aren't equally stable. My five test questions are
written carefully; real ones aren't. So I re-asked the same facts the way a
person actually types:

| Typed question | Best distance | Top source |
|---|---|---|
| `laundry calder how much` | 0.1979 | housing_calder_annexe_laundry.txt |
| `can i still switch to pass fail after midterms??` | 0.5002 | admin_pass_fail_option.txt |
| `shuttle weekend` | 0.5421 | transit_shuttle.txt |
| `phys 130 final exam?` | 0.3080 | course_phys_130.txt |
| `is the food at the atrium any good` | 0.4538 | dining_the_atrium.txt |
| `what happens if i drop a class late` | 0.4119 | admin_add_drop_deadline.txt |

The same fact moves from 0.19 to 0.54 depending on phrasing, and every one of
these is a question the corpus definitely answers. The out-of-scope group didn't
move at all — it never came below 0.825 however I phrased it. **In-corpus
distance is sensitive to phrasing; out-of-corpus distance isn't.** So the cutoff
belongs high in the gap, not in the middle of it.

0.70 leaves 0.16 of headroom above the worst genuine question I could produce
and still sits 0.12 clear of the nearest out-of-scope one. The default 0.6 would
have left 0.06 and refused `shuttle weekend`. At 0.70 the gate refuses 5 of 5
out-of-scope questions and admits 5 of 5 real ones.

## How I Used AI

**1. The chunker, where the reasoning was confident and wrong.** I described the
corpus structure to Claude — title line, blank line, short paragraphs — and
asked it to design a chunking strategy. It came back with paragraph-splitting
and a good-sounding argument: each paragraph is one idea, the documents are
already laid out that way, splitting on blank lines respects the author's own
structure. It also predicted the failure mode would be wrong source attribution,
because the dorm families share paragraphs verbatim.

Rather than build it, I asked for a script that would build it as a throwaway
index and count what came out. That changed the answer. Paragraph-splitting
produced 271 chunks of which 88 — every title line in the corpus — were
content-free headings, and those headings ranked #1 for four of eight probe
questions. The predicted failure (wrong attribution) hardly showed up at all.
The argument had been entirely plausible and the measurement contradicted it, so
the strategy I actually shipped is close to the opposite: keep documents whole,
and make short chunks impossible by construction. The thing AI was most useful
for here was writing the experiment that proved its own suggestion wrong.

**2. The threshold, where the textbook answer was the wrong one.** Once I had
the two groups of distances — 0.187–0.411 in corpus, 0.825–0.934 out — I gave
them to Claude and asked where the cutoff belonged. It said the midpoint, 0.618,
and the reasoning was sound as far as it went: the gap is empty, the midpoint
maximises the margin on both sides, and it's more or less what the milestone
instructions describe when they say to put the cutoff in the gap.

What bothered me is that it treats the two groups as if they're the same kind of
thing. My five test questions are written carefully, once, by me. Real questions
aren't. So before accepting 0.618 I re-asked the same facts the way someone
actually types them — `shuttle weekend`, `can i still switch to pass fail after
midterms??` — and the in-corpus distances climbed to 0.542 for facts the corpus
definitely contains, while the out-of-scope group didn't move at all. The gap
isn't symmetric, so its midpoint isn't the right place to stand.

I moved the cutoff to 0.70 and wrote the six awkward phrasings into the README
as the evidence. What I changed wasn't really the number — it was noticing that
a recommendation can be correct about the data I handed over and still wrong
about the data I hadn't thought to collect.

<!-- No stretch features attempted in unit 1. -->

---

# Unit 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

`python run_eval.py --label before` → [`results/run_2026-09-23_2139_before.md`](results/run_2026-09-23_2139_before.md).
15 model calls, cache off, 9,227 tokens.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. No chunk is a heading with nothing under it | 0 orphans of 88 | 0/88 | 0/88 | 0/88 | MET |
| 5. The cited source contains the answer | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |

Criteria 1, 3 and 4 are the same in all three columns, and that's correct
rather than lazy. Retrieval is deterministic, the gate is a comparison against
a fixed number, and the chunker is a pure function of the documents — none of
them can vary between runs. Only 2 and 5 depend on the model, and those are the
ones I expected to move. They didn't.

**A note on how these were scored.** `run_eval.py` gives one pass/fail per
*question* via `scorer.py::judge`; the table above is one row per *criterion*,
so criteria 1, 2, 4 and 5 were aggregated from the run-log transcript rather
than read off it. Criterion 1 is measured against the retrieved chunks
(`store.py::search`), not the answer text — a correct answer built from a chunk
that doesn't contain the fact would pass criterion 2 and fail criterion 1, and
I wanted those separable.

I also had to fix `scorer.py` before trusting any of this. My first version
read `answer or "".lower` — missing parentheses, so an empty answer raised
`TypeError` instead of scoring False — and it lowercased `expects` but not
`answer`, so "week eight" scored True while "Week eight" scored False. The
model's capitalisation varies between runs, so that bug would have turned
formatting into correctness in the exact number Milestone 1 asks me to test
three times. Found by testing the scorer against hand-written cases rather than
by reading it.

### Real output

**Criterion 1 and 5** — produced by `run_eval.py::run_once`, retrieval by
`store.py::search`, chunks by `chunker.py::split_documents`. This is the
question I expected to fail: three of the five chunks retrieved are laundry
posts for the *wrong* buildings, at $1.75, $1.75 and $1.50.

```
### What does a wash cost in Calder Annexe? — run 1

- Best distance: 0.2542 (passed the gate)
- Sources retrieved: housing_aldridge_hall_laundry.txt, housing_calder_annexe.txt, housing_calder_annexe_laundry.txt, housing_innisfree_hall_laundry.txt, housing_old_brewhouse_laundry.txt

A wash costs $2.00 in Calder Annexe. 

Sources: housing_calder_annexe_laundry.txt, housing_calder_annexe.txt
```

**Criterion 2** — produced by `generate.py::answer_from_chunks`. All 15
question-runs named at least one source. Run 3 of the same question shows the
format drifting while the citation stays correct:

```
A wash costs $2.00 in Calder Annexe (housing_calder_annexe.txt and housing_calder_annexe_laundry.txt).
```

```
### How late can I declare a course pass/fail, and what grade do I need to pass it? — run 1

- Best distance: 0.2087 (passed the gate)
- Sources retrieved: admin_add_drop_deadline.txt, admin_declaring_a_major.txt, admin_grade_appeals.txt, admin_graduation_requirements.txt, admin_pass_fail_option.txt

You can declare a course pass/fail as late as week eight, and you need a grade of C- or better to pass. 

Source: admin_pass_fail_option.txt
```

**Criterion 3** — produced by `run_eval.py::check_out_of_scope`, cutoff 0.70,
one deterministic pass. No model calls: a refused question never reaches the
model.

```
| Out-of-scope question | Best distance | Gate |
|---|---|---|
| What is the capital of Mongolia? | 0.825 | refused |
| How do I change the oil in a diesel engine? | 0.934 | refused |
| Who won the 1994 World Cup? | 0.886 | refused |
| What is the recommended dosage of ibuprofen for a headache? | 0.844 | refused |
| How do I write a for loop in Rust? | 0.896 | refused |
```

**Criterion 4** — produced by `chunker.py::split_documents`, counted over all
88 chunks rather than the 5 I sampled:

```
chunks: 88; under 100 chars: 0; missing title: 0
shortest chunk: 178 chars
=> 0 orphans
```

## Verdicts

| # | Criterion | Target | Runs | Verdict | How I decided |
|---|---|---|---|---|---|
| 1 | Retrieved chunk contains the answer | 4 of 5 | 5/5, 5/5, 5/5 | **MET** | Checked against the retrieved chunks, not the answer text: for all five questions one of the top-5 chunks literally contains the `expects` string from `questions.py`. Clears the target with one to spare. |
| 2 | Every answer names a source | 5 of 5 | 5/5, 5/5, 5/5 | **MET** | All 15 question-runs contain at least one `*.txt` filename. Phrasing wandered — "Sources:", "Source:", inline in parentheses — but the criterion asks whether a source is named, not how. |
| 3 | Gate stops out-of-corpus questions | 4 of 5 | 5/5, 5/5, 5/5 | **MET** | All five OUT_OF_SCOPE questions landed at 0.825–0.934 against a 0.70 cutoff. The nearest miss had 0.125 of margin, so this isn't a close call. |
| 4 | No chunk is a heading with nothing under it | 0 orphans of 88 | 0/88, 0/88, 0/88 | **MET** | Counted over all 88 chunks, not the 5 I sampled: none under 100 characters, none missing its title line, shortest is 178. The floor in `chunker.py::_pack` makes this true by construction. |
| 5 | The cited source contains the answer | 5 of 5 | 5/5, 5/5, **4/5** | **MISSED** | Run 3 of the PHYS 130 question cited `course_phys_130_workload.txt`, which says nothing about midterms or finals. Two runs out of three is not the target. |

### How I decided criterion 5, since it's the one that turns on a reading

My first pass scored this 5/5, 5/5, 5/5 and I nearly wrote MET. The lenient
reading is "did the answer name a correct source" — and it always did, because
every answer named two or three files and at least one was right.

Then I scored it the strict way: is *every* file it named one that actually
contains the answer? That gives 5/5, 5/5, 4/5.

I went with the strict reading, because it's what I wrote. The criterion says
"the document named in the answer is the document that actually contains the
answer — **not merely a plausible-looking neighbour**", and
`course_phys_130_workload.txt` is precisely a plausible-looking neighbour: same
course, adjacent filename, and it contains hours per week rather than exam
format. If I score that as MET, the clause I wrote to catch this exact failure
catches nothing, and criterion 5 collapses into criterion 2.

So: **MISSED.** Two good runs and one bad one is not "all 5 of my test
questions".

## Diagnoses

One miss, criterion 5.

**Stage: generation.** Not retrieval, and I checked rather than assumed —
retrieval returned `course_phys_130_exams.txt` at rank 1 with the answer in it,
so everything the model needed was present and correctly ranked. The failure
happened after that.

**Mechanism.** Retrieval for this question returns three PHYS 130 documents in
the top five — `course_phys_130.txt`, `course_phys_130_exams.txt` and
`course_phys_130_workload.txt`. Two of them contain the exam format; the third
is about workload. The grounding prompt's rule is:

```
- Name the document your answer came from, using the filename given in each excerpt.
```

That asks which document the answer came from, but nothing in it rules out
naming a document that's merely on the same subject. Given three excerpts all
headed `PHYS 130 Mechanics`, the model treated "documents about this course" as
"documents supporting this claim" and listed all three. It did this on one run
of three, which fits: nothing in the prompt forbids it, so whether it happens is
left to sampling.

**The pattern, and the part I didn't expect.** This only fired on the question
whose retrieval pulled three documents from the same family. The Calder Annexe
question pulled two Calder documents and cited both — and both genuinely contain
`$2.00`, so it scored correct. The failure needs a family member that's
on-topic but factually irrelevant, and PHYS 130 was the only question that had
one in its top five.

What's uncomfortable is that my own Unit 1 chunking decision made this more
likely. Stapling the title line onto every chunk is what lets retrieval tell
Calder from Aldridge — but it also means all three PHYS 130 chunks announce
`PHYS 130 Mechanics` at the top, so within a family every chunk looks equally
citable. The fix for criterion 5's near-duplicate problem in unit 1 is feeding
criterion 5's over-citation problem in unit 2. I don't think that makes the
chunking wrong; it means the disambiguation has to happen in the prompt too,
not only in the chunk.

### On the four I didn't miss

Four of five MET on the first run means my targets had room in them, and I'd
rather say that than claim the system is excellent.

Criterion 3 is the softest. I set 4 of 5 predicting that a broad corpus would
let an out-of-scope question drift close on vocabulary alone — I named ibuprofen
and Rust as the likely leaks. Neither came near: the tightest was 0.825 against
a 0.70 cutoff. **I'd tighten it to 5 of 5, and add out-of-scope questions
designed to be adjacent to the corpus rather than obviously foreign** — "what's
the cheapest dorm laundry at the university across town", "how do I appeal a
parking ticket in the city" — questions that share vocabulary with campus_life
but have no answer in it. The current five are from a different world entirely,
which made the target easy.

Criterion 1 is next softest, for a reason I already had evidence for and didn't
act on. It's measured against five carefully-written questions, and in unit 1 I
showed that re-typing the same facts casually pushes distances from 0.19 to
0.54. **I'd tighten it to 4 of 5 on casually-phrased questions**, which is a
harder test of the same property.

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

## The Improvement

**What I changed:**

**Why I picked it:**

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->

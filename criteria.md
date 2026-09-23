# Acceptance criteria — The Unofficial Guide

Five criteria that say what "working" means for this system, written in unit 1
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"Retrieval works"* is an opinion. *"For at
least 4 of my 5 test questions, the top results include a chunk containing the
answer"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter or looser one. A reason that says something about your corpus or your
pipeline earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## 1. Retrieved chunks contain the answer

For at least 4 of my 5 test questions, the retrieved chunks include one that
contains the answer.

**Why this target:** Two of my five questions (Q1, laundry prices in Calder
Annexe; Q4, the PHYS 130 exam format) ask about one member of a family of
near-identical documents. `campus_life` documents seven dorms and nine courses
in parallel, and the laundry files for Aldridge and Calder differ only in two
dollar amounts — the rest of the paragraph is word-for-word the same. Retrieval
has to separate documents that are mostly the same text, so I'm allowing for one
of those two to come back with a sibling building's chunk instead. I'm not
setting it at 3 of 5, because the distinguishing name sits in each document's
title line, and that gives retrieval something real to grip.

---

## 2. Every answer names a source

Every answer the system produces names at least one source document.

**Why this target:** All five and not four, because this one doesn't depend on
retrieval being good — only on the prompt being obeyed. `generate.py` puts the
source filenames in the prompt and asks for them back, and every chunk carries
its filename in metadata through `store.py::search`, so a missing source means
the model ignored an instruction rather than that the pipeline lost the
information. One failure out of five would be a real defect worth chasing, so I
don't want a target that lets me shrug at it. Note this criterion only asks that
a source is *named* — whether it's the *right* source is criterion 5, and on
this corpus those are genuinely different questions.

---

## 3. The relevance gate stops out-of-corpus questions

When I ask a question my documents clearly don't cover, the relevance gate
stops it and the system returns "I don't have enough information about that" —
in at least 4 of 5 tries.

<!-- The five questions are the ones in `OUT_OF_SCOPE` at the bottom of
     `questions.py`, and `run_eval.py` puts them through the gate and writes
     what happened into your run log. Swap them for your own if you'd rather —
     just keep five of them, or the "4 of 5" above has nothing to be 4 of. -->

**Why this target:** 4 of 5 rather than 5 of 5 because one cutoff has to serve
two jobs that pull against each other. `campus_life` is a broad corpus — dining,
dorms, courses, money, transit, health, weather — so a question from outside it
can still land near something on vocabulary alone. "What is the recommended
dosage of ibuprofen for a headache?" has a health centre document to drift
toward, and "How do I write a for loop in Rust?" has CS 210. I expect those two
to be the closest of the five out-of-scope questions, and a cutoff loose enough
to answer my real questions may not refuse both. I'd rather set the cutoff where
the in-corpus questions all still work and accept one leak than refuse a genuine
question to protect this number.

<!-- The actual distances, and where the gap turned out to be, are measured in
     Milestone 4 and recorded in the README's ten-row table. -->


---

## 4. No chunk is a heading with nothing under it

Every chunk my chunker produces is at least 100 characters long **and** contains
the title line of the document it came from. Zero chunks out of however many are
title-only. I check this by running the chunker over the whole corpus and
counting, not by eyeballing the five I paste into the README.

**Why this target:** All 88 documents in `campus_life` are built the same way: a
short title line naming the thing ("Laundry in Calder Annexe", "On the printing
quota"), a blank line, then two or three short paragraphs. That title line is
the only place the specific building or course name reliably appears — the
paragraphs underneath say "the dryers back up on Sunday evenings" without ever
repeating which building's dryers.

So the title line is doing two jobs at once, and any chunking rule that splits
on blank lines breaks both. It strands the title as a chunk with no content in
it, and it strips the identifying name off the paragraph that actually holds the
answer. 100 characters is the floor because the shortest *complete* document in
the corpus is 178 characters; anything that comes out under 100 can't be a whole
document and is therefore a fragment of one.

---

## 5. The source named is the source the answer came from

For all 5 of my test questions, the document named in the answer is the document
that actually contains the answer — not merely a plausible-looking neighbour. I
check it by hand against the corpus file, because only I know which file holds
the real answer.

**Why this target:** Criterion 2 is satisfied by naming any source at all, and
on this corpus that is close to free. `campus_life` has seven dorms and nine
courses written up in parallel with near-identical wording, so an answer about
laundry prices that cites *some* laundry document looks completely correct until
you check which building it is. Aldridge charges $1.75 to wash and Calder
charges $2.00, and a confident answer citing the wrong file is worse than a
refusal, because there's nothing in the output that signals it's wrong.

All 5 and not 4 because this is the failure mode I'd most want to know about,
and grading it leniently would hide exactly the thing I built the criterion to
catch. If I miss it, I'd rather the number say so.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 2 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 1. Retrieved chunks contain the answer

         For at least 4 of my 5 test questions, the retrieved chunks include
         one that contains the answer.

         **Why this target:** ...

         > **Revised in unit 2:** For at least 4 of 5 questions, the top three
         > results contain the answer.
         >
         > **Why revised:** I couldn't judge "the chunks include one that
         > contains the answer" the same way twice — I scored two questions
         > differently on Monday than on Wednesday. The new version is
         > something I can actually check.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said 4 of 5 but got 2 of 5, so 2 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.

     The whole reason the originals stay visible is so someone can see what you
     said before you knew the answer.
     ───────────────────────────────────────────────────────────────────────── -->

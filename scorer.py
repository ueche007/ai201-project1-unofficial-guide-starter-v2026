"""
The scorer run_eval.py looks for.

`judge` decides, for one question on one run, whether the answer counts as
correct. Correct here means: the answer contains the fact I said in
questions.py I'd expect to see — the `expects` string I wrote in unit 1,
before I had any results.

Two bugs in my first version, both found by testing the scorer itself rather
than by reading it:

  1. `answer or "".lower` — missing parentheses, so on an empty answer this
     returned a method object and `in` raised TypeError instead of False.
  2. It lowercased `expects` but not `answer`, so "week eight" scored True and
     "Week eight" scored False. The model capitalises unpredictably between
     runs, so that turned a property of the answer's formatting into a
     property of the answer's correctness — and this is the number Milestone 1
     asks me to test three times and trust.
"""


def judge(question: str, expects: str, answer: str, results) -> bool:
    """
    True if the answer contains the expected fact.

    Substring matching is crude and I know it. It can't tell "three midterms"
    in a correct answer from "three midterms" inside a hedge, and it would
    credit an answer that named the right number for the wrong building. What
    it can do is apply the same rule to all fifteen runs without me getting
    more generous as the evening goes on, which hand-scoring could not.
    Criterion 5 is where the wrong-building case actually gets checked.
    """
    if not expects:
        return False

    needle = expects.strip().lower()
    haystack = (answer or "").lower()
    return needle in haystack

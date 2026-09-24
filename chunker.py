"""
Stage 2 of the pipeline: splitting documents into chunks.

⚠️ THIS IS THE FILE YOU CHANGE IN MILESTONE 3.

`split_documents` below is deliberately plain. It cuts every document into
fixed-size pieces with a fixed overlap and pays no attention to where sentences
or paragraphs end. It works, and it is not good.

On a corpus of short posts it may not cut anything at all: `campus_life` comes
out as 88 documents and 88 chunks, because almost nothing in it reaches 800
characters. That is the baseline, not a bug — Milestone 3 is where you decide
whether one post should stay one chunk.

Your job in Milestone 3 is to replace the *body* of `split_documents` with a
strategy that fits the documents you actually read in Milestone 1. Keep the
name and the shape of what it returns — the rest of the pipeline calls it, and
your README has to name the function that produced your chunks.

If you get stuck for 30 minutes, `fallback_split` is the original. Switch back
to it, write down what you saw, and move on. That's a real observation about
your pipeline, not giving up.
"""

import re
from dataclasses import dataclass

import config
from ingest import Document


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in unit 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


# ─── Milestone 3: my chunking strategy ───────────────────────────────────────
#
# Every document in campus_life is shaped the same way: a short title line
# naming the thing, a blank line, then two or three short paragraphs.
#
#     Laundry in Calder Annexe
#
#     Machines take $2.00 wash, $1.75 dry, app-based. There are eight washers
#     and six dryers for the building, ...
#
#     Best time to do laundry here is Tuesday or Wednesday morning. ...
#
# Two things about that shape drive everything below.
#
# First, the title line is the ONLY place the building or course name reliably
# appears. The paragraphs underneath say "the dryers back up on Sunday
# evenings" without ever saying whose dryers. So a chunk that has been
# separated from its title has lost the one word that tells seven otherwise
# near-identical laundry documents apart.
#
# Second, splitting on blank lines — the obvious move for documents laid out
# like this — turns all 88 title lines into their own chunks. I measured it:
# 271 chunks, 88 of them (32%) a bare heading with no content, and one of those
# content-free headings ranked #1 for four of eight probe questions. They match
# beautifully on topic and answer nothing.
#
# Hence: a size CEILING that this corpus never reaches, a size FLOOR that makes
# orphans impossible, and the title line stapled to every piece.

TITLE_MAX_CHARS = 80    # a first block longer than this is prose, not a title
MIN_CHUNK_CHARS = 100   # criterion 4's floor — below this it's a fragment


def _split_title(text: str) -> tuple[str, str]:
    """
    Separate a document's title line from its body.

    Returns ("", text) for anything that doesn't open with a short standalone
    line, so a document that breaks the corpus convention still chunks sanely
    instead of losing its first paragraph to a bad guess.
    """
    blocks = text.split("\n\n", 1)
    if len(blocks) == 2:
        head = blocks[0].strip()
        if head and len(head) <= TITLE_MAX_CHARS and "\n" not in head:
            return head, blocks[1].strip()
    return "", text.strip()


def _pack(paragraphs: list[str], budget: int) -> list[str]:
    """
    Group paragraphs into pieces no longer than `budget`, never cutting inside
    a paragraph unless one is longer than the budget all by itself.

    This is where the floor is enforced: a piece that would come out under
    MIN_CHUNK_CHARS is merged into the one before it rather than emitted. That
    is what makes a title-only or fragment chunk impossible by construction.
    """
    pieces: list[str] = []
    current = ""

    for para in paragraphs:
        # A single paragraph over budget: split it on sentence boundaries so a
        # fact is never severed mid-sentence the way fallback_split does it.
        if len(para) > budget:
            if current:
                pieces.append(current)
                current = ""
            sentences = re.split(r"(?<=[.!?])\s+", para)
            buf = ""
            for sentence in sentences:
                if buf and len(buf) + 1 + len(sentence) > budget:
                    pieces.append(buf)
                    buf = sentence
                else:
                    buf = f"{buf} {sentence}".strip()
            if buf:
                current = buf
            continue

        if current and len(current) + 2 + len(para) > budget:
            pieces.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}".strip()

    if current:
        pieces.append(current)

    # Enforce the floor: fold anything too small back into its neighbour.
    merged: list[str] = []
    for piece in pieces:
        if merged and len(piece) < MIN_CHUNK_CHARS:
            merged[-1] = f"{merged[-1]}\n\n{piece}"
        else:
            merged.append(piece)

    return merged


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    Split documents so that every chunk is a complete thought that still says
    what it is about.

    The rules, in order:

      1. Peel off the title line.
      2. If title + body fits in CHUNK_SIZE, the document stays whole. On
         campus_life this is every document — the longest is 549 characters
         against a 600 ceiling — so 88 documents produce 88 chunks.
      3. Otherwise pack whole paragraphs up to the ceiling, splitting inside a
         paragraph only on sentence boundaries and only if one paragraph
         exceeds the ceiling on its own.
      4. Prepend the title line to every piece, so no chunk ever loses the
         name of the building or course it describes.
      5. Merge anything under MIN_CHUNK_CHARS into its neighbour.

    Rule 2 means this corpus is never actually cut. That is the finding, not a
    shortcut: these documents are already the size of one idea, and the work
    that matters here is rules 4 and 5, which is what stops the obvious
    paragraph-splitting approach from wrecking retrieval.
    """
    chunk_size = config.CHUNK_SIZE
    chunks: list[Chunk] = []

    for doc in documents:
        title, body = _split_title(doc.text)

        if len(doc.text) <= chunk_size:
            pieces = [doc.text.strip()]
        else:
            # Reserve room for the title I put back on each piece below.
            budget = max(chunk_size - len(title) - 2, MIN_CHUNK_CHARS)
            paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
            pieces = [
                f"{title}\n\n{piece}" if title else piece
                for piece in _pack(paragraphs, budget)
            ]

        for index, piece in enumerate(pieces):
            chunks.append(
                Chunk(
                    text=piece,
                    source=doc.source,
                    index=index,
                    produced_by="chunker.py::split_documents",
                )
            )

    return chunks


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))

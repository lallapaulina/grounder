# grounder
This repo explores reducing *human*-hallucinated citations, i.e., regular citations, created by humans, that point to real texts but not, unfortunately, texts that offer the support the citer seeks. Imagine if, for each `\cite`, it were easy to list *how* the cited source supports our text, helping us catch errors and express care for our readers!

The idea is to work through a manuscript, citation by citation, extracting the text related to the current citation and searching the cited source for supporting text. LLMs do the searching (on pre-processed pdfs stored locally), but the putative supporting text is then extracted deterministically from the local pdfs. 

# Citation Evidence Audit (minimal Python prototype): 

A local-first, bare-bones tool for checking what cited research papers **actually say**. It walks a LaTeX manuscript's citations in order and proposes evidence from PDFs you already have. The model **never supplies the quotation**: it returns existing passage IDs, and Python extracts and verifies their text against an archived, SHA-256-checked PDF. The **manuscript author**, not the model, judges whether the cited source truly supports a claim.

**The three gates:** (1) an LLM suggests source passage IDs and gives a *tentative* interpretation; (2) ordinary Python checks the PDF hash and exact extracted passage and rejects fabricated IDs; (3) the author accepts, rejects, or overrides the selection in `review.csv`.

Version 0 uses **PyMuPDF** for PDF extraction; the optional model call is an HTTPS request to OpenAI's Responses API.

## tl;dr
General idea: 

Read a LaTeX manuscript and its bibliography.

Process locally stored research-paper PDFs.

Use an LLM to identify potential supporting passages.

Verify that those passages exist in the stored source text.

Generate a report for us to review.


## Install

Requires **Python 3.10+**.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Organize *your own* files as follows (the input filenames match the **BibTeX citation keys**, case-sensitively):

```text
my-project/
  manuscript.tex
  references.bib
  papers/
    smith2020.pdf
    jones2022.pdf
```

Only PDF files corresponding to cited keys are necessary. Example: `\citep{smith2020,jones2022}` expects both named PDFs. The `.bib` file is used for DOI and source links; it is not used to determine passage contents. 

## Run

```bash
python audit.py prepare --tex my-project/manuscript.tex \
  --bib my-project/references.bib --papers my-project/papers --work work
```

`prepare` writes:

- `work/claims.csv` — one row per citation occurrence in **manuscript order**; **read and edit the automatically extracted claim strings** before invoking the model.
- `work/archive/<SHA256>.pdf` — immutable-in-principle local content-addressed PDF copies. Existing archives are checked; overwritten or corrupted ones cause a hard failure. Keep `work/` private.
- `work/passages/<citekey>.json` — passage ID, exact extracted text, PDF page number, bounding box, and SHA-256.
- `work/manifest.json` — metadata and links to source.

For a free local sanity check (no API key and **no LLM assessment**):

```bash
python audit.py analyze --work work --offline
```

To ask the model to propose passage IDs and explain its *provisional* support assessment:

```bash
export OPENAI_API_KEY='YOUR_KEY'  # PowerShell: $env:OPENAI_API_KEY='YOUR_KEY'
python audit.py analyze --work work --model gpt-5-mini
```

**Important:** don't commit API keys. `OPENAI_API_KEY` is read only from your environment. The API sends extracted passage text and manuscript claim text to the model; it does **not** upload complete PDFs. On the server, `store=false` is requested. Read the provider's privacy/data handling terms before using unpublished material. API usage is billed separately from a ChatGPT subscription.

This produces `work/report.html`, `work/decisions.json`, `work/review.csv`, and a small cache of previous responses. **Opening `work/report.html` locally is sufficient** (no web server necessary). An unsuccessful model request exits with an error rather than fabricating evidence; previously completed calls are cached per claim, PDF hash, model, and prompt.

## Human review and overrides

Open `work/report.html`, check the **actual source PDF**, and edit `work/review.csv`:

```csv
citation_id,citekey,source_sha256,claim_sha256,decision,passage_ids,notes
C0001,smith2020,<PDF_hash>,<claim_hash>,accepted,p0002_b0004,Passage qualifies the claim
C0002,jones2022,<PDF_hash>,<claim_hash>,rejected,,This is not the correct source
```

Do not literally type `<PDF_hash>` or `<claim_hash>`; leave the generated SHA-256 values in place. Allowed decisions: `pending`, `accepted`, `rejected`, `needs_review`. The model's passage IDs will appear in the HTML report; to override them, put one or more real source passage IDs separated by semicolons in `passage_ids`. For other available IDs, inspect `work/passages/<citekey>.json`. If a manual ID is invalid, **no quote is produced for that ID**, and the report flags it.

Then regenerate the report without spending more API tokens:

```bash
python audit.py render --work work
```

If either the PDF **or the associated claim** changes, previous human approval is flagged **stale** until re-reviewed. The current hashes appear in the HTML report; after genuinely re-reviewing, update the `source_sha256` and/or `claim_sha256` cell to the current value and set the appropriate review decision. Rerun `analyze` if the claim/source changed, because the old model assessment is also stale. If the manuscript itself changed, `prepare` refreshes the auto-detected claim instead of silently reusing an older manual edit. The application re-extracts original PDF text and compares it to indexed text before rendering; any mismatch is a hard error.

## Try without your own papers or an API key

```bash
python demo/make_demo.py
python audit.py prepare --tex demo/manuscript.tex --bib demo/references.bib \
  --papers demo/papers --work demo/work
python audit.py analyze --work demo/work --offline
# Open demo/work/report.html
```

The demo contains **invented source content only**; it does not reproduce a copyrighted paper. For a real evidence-search demonstration, rerun `analyze` without `--offline` after setting a key.

## Guarantees and limitations

**Mechanically enforced:** Model-proposed IDs must be among blocks actually sent to it. Quotation text is never accepted from the LLM. Python checks the original archived PDF's SHA-256 and independently re-extracts the exact text block before including it in the report. A report cannot silently show an invented model quote as original PDF text. Quotes are **machine-extracted PDF text**, not a visual or semantic verification of the original typesetting.

**Not guaranteed:** An actual passage can fail to justify a claim. The model's `direct`, `partial`, `indirect`, `none`, or `uncertain` classification is advisory. **The author** makes the substantive determination; no second LLM is used as a verifier. `none` means no support found **in the screened passages**, not that support does not exist elsewhere.

This intentionally small MVP has important scope limits:

- **Input is one `.tex` file**, not an entire multi-file project, and supports common `\cite`, `\citep`, `\citet`, `\citealt`, `\citealp`, `\parencite`, `\textcite`, `\autocite` variants with up to two optional arguments. Unusual LaTeX macros, `\input` files, `\nocite`, footnotes, BibLaTeX refinements, and citation commands defined by the user are not handled. Verify `claims.csv` before sending requests. Multi-key citations produce separate evidence records with the same claim context.
- Sentence extraction is heuristic, not syntactic analysis, and can misread abbreviations, formulas, or long paragraphs. The human can edit `claims.csv` directly.
- PDF text blocks aren't guaranteed to align with semantic paragraphs or reading order. Tables, equations, figures, multi-column layouts, math notation, and scanned/OCR-only PDFs may be misinterpreted or omitted. Review the original PDF. PDF pages are **file pages**, not journal page labels. No built-in OCR.
- When extracted source text fits **48,000 characters**, all blocks are sent to the model. Longer papers send up to 40 lexically retrieved blocks within that budget. Retrieval can miss relevant material. The HTML report flags partial-paper screening, and every screened ID is available for manual override.
- There is no automatic paper lookup or download, bibliography correction, automatic academic judgment, or integrated graphical review editor. Each PDF must be named according to the citation key.
- Running on a large manuscript may incur API cost. No retry loop is implemented; this intentionally fails clearly on network/API errors. A restart reuses completed calls.
- `work/` includes copyrighted PDFs and manuscript excerpts; it is excluded in `.gitignore`. Do **not** publicly publish or redistribute archived publisher PDFs unless you have permission. The generated report may also contain copyrighted excerpts; review rights and journal requirements before publishing it.
- A report is a **review artifact**, not a publisher-ready or externally hosted scholarly evidence archive. A stable, public supplementary archive may require additional packaging, links, licenses, and human approval.

## Test

```bash
pip install pytest
pytest -q
```

Tests cover citation order, comment handling, nested BibTeX fields, local PDF hashing, true-versus-invented passage IDs, model response caching, manual override, and stale author reviews. Mock model calls mean tests require **no API key**. Includes a mocked HTTPS request test for the model call.

## Maybe To Do
Enable multi-file projects, not just single .tex manuscript file
Try more sophisticated pdf parsers -- watch out, though!
Make output fancy
Extract candidate text from .bib `\notes` if manuscript author has been disciplined and entered real quotes there... 

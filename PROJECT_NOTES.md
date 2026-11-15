# Project notes

The working memory of this project: how we work, what was decided and why,
and what comes next. Read this first at the start of every new session.
Update it whenever a decision is made.

The source of truth is this file in the repository. A copy lives in the docs
of the Claude project "Korean Learning App"; update both together.

Last updated: 15 November 2026

---

## 0. Current status (start here)

- v0.1 runs on my Mac (Python 3.15). All code changes up to the grammar list,
  two gaps, tutor comments and batches are committed (9 November).
- **Third run done (15 November):** the 27 October notes are saved with the
  current prompt: 29 cards, 93 practice items, 11 grammar forms, no reviews
  yet. (Saved first with the date 15.11; Claude corrected it to 27.10.)
  Check of the prompt fixes: 쇼핑 해요 corrected, every card has a gap,
  꽁짜 not marked as a correction; **년도 still has no look-alike note.**
- Fix (10 November, tests pass): output limit 32,000 tokens, the answer
  is streamed, and the page shows "Writing card N…" while it arrives. After
  each run the review page shows the tokens used, the time and the effort.
- **Effort comparison (run 15 November):** `python experiments/compare_effort.py`
  ran the 27 October notes at effort high and medium, one run each; answers
  in `data/experiments/`. High: 29 cards, 36 gap items, 14,151 tokens, 113 s
  (the two earlier high runs hit 16,000: large run-to-run variation).
  Medium: 28 cards, 29 gap items, 7,594 tokens, 47 s; it skipped breakdowns
  on 3 sentences, gaps on 5 cards and the example for 잘됐다, and marked 꽁짜
  as a correction (against rule 1). Medium was better on one point: it
  corrected the spacing in 쇼핑 해요. **Decided: keep high** (no code change).
- Prompt fixed (15 November): spacing of noun + 하다 verbs (rule 1), every
  card gets a gap, now required by the schema (rule 9), look-alikes checked
  in sentences too (rule 10).
- **Next:** run `python -m unittest` (18 tests) and commit; add the 년도 note
  by hand on My cards; then use the app for real for about a week. After
  that: my SQL progress page and option A (embeddings).
- From 9 November we continue in new chats inside the Claude project
  "Korean Learning App".

## 1. Goal

A personal Korean learning app built around my own lesson notes, used every
week. It is also my portfolio project, and from November 2026 it doubles as
gentle preparation for my Roche internship (AI projects using embeddings, RAG,
SQL, Linux; starts 11 January 2027).

**The app has to stay fun.** Nothing in it is required for the job. If a
session feels like homework, stop.

## 2. How we work

- **Split.** Claude builds the plumbing (database, AI calls, practice screens,
  embeddings). I write the progress and weak spots page myself, in **SQL**, and
  the analysis experiments (for example the embedding model comparison).
- **Commits.** Claude writes files into the project folder. I review every
  change in GitHub Desktop and commit and push myself.
- **Conversation style.** Claude states its opinion first with the counter
  case, flags any deviation from what I asked, raises disagreement only when
  it matters (and then presses), asks calibration questions as options, and
  checks in on how I am finding the process on decisions with real stakes.
- **Honesty in the README.** The app is built with Claude as a coding
  assistant, and the README says so.

## 3. Setup

| What | Where / value |
|---|---|
| Repository | github.com/jasminsonego/korean-learning-app (public, MIT) |
| Local folder | `~/Developer/korean-learning-app` (deliberately not in iCloud Documents) |
| Python | 3.15 in `.venv` (3.13 is the fallback if a package lacks 3.15 support) |
| Tools | GitHub Desktop, VS Code, Terminal in VS Code |
| API key | `.streamlit/secrets.toml` (ignored by Git), model `claude-sonnet-5-5` |
| My data | `data/korean.db` (ignored by Git) |

Start: `source .venv/bin/activate`, then `streamlit run app.py`.
Tests: `python -m unittest`.

## 4. How the app works

```
notes + tutor comments + grammar list ──► Claude (structured output) ──► draft cards
                                                                            │ review
progress page ◄── reviews ◄── practice in batches ◄── FSRS ◄── cards + items ◄┘
```

- **cards**: one learnable thing (word, sentence, grammar). **items**: one
  way of practising it (Korean to English, English to Korean, gap, second
  gap), each with its own FSRS schedule. **reviews**: every answer.
  **grammar**: forms already explained. **settings**: batch size.
- Files: `korean_app/ai.py` (prompt and schema), `korean_app/db.py`
  (database), `korean_app/ui.py` (shared UI), `views/` (pages), `tests/`.

## 5. Decisions log

| Date | Decision | Why |
|---|---|---|
| 26.10. | Korean app instead of R Shiny dashboard; Python + Streamlit + SQLite | Fun project I use myself; data work at the core; get better at Python |
| 26.10. | Built for one user, web app, one feature set at a time | Logins, native apps and "platform" scope would stop it from shipping |
| 27.10. | AI structures pasted notes (not a manual form) | Notes mix words, sentences, grammar and half translations |
| 27.10. | Reveal and rate in v0.1, typing answers later | Simpler first version |
| 27.10. | FSRS for scheduling | Modern spaced repetition algorithm with a Python library |
| 08.11. | Structured outputs instead of a forced tool call | The current model rejects forced tool calls (400 error) |
| 08.11. | Batches of N new items (set in the app) instead of a daily limit | I want to study in sets and start the next set when ready |
| 08.11. | "Continue now" for cards that come back later the same day | Avoid waiting 10 minutes at the end of a batch |
| 08.11. | "Corrected" marks only wrong Korean or wrong meanings; English typos fixed silently | Round 1 flagged trivial things and buried the real corrections |
| 08.11. | Gap on a word card must be that word | Round 1 blanked unrelated new words (양말) |
| 08.11. | Synonyms in one lesson get hints ("free (casual)") | English to Korean must have one right answer |
| 08.11. | Word parts decided case by case (-화 grammar card; 장 a word) | My tutor says 장 is also used alone; 화 alone means anger |
| 08.11. | Unclear items: "(guess) ..." + uncertain marker + question | My choice: see the guess, but clearly labelled |
| 09.11. | Breakdown: particles as separate entries (-은 = topic marker), dictionary forms in brackets (많아요 (많다)) | Clearer grammar |
| 09.11. | Grammar list: the AI explains forms not on the list once per lesson and proposes new ones, which I tick to add | No repeated explanations of basics; list grows automatically |
| 09.11. | Up to two gaps per sentence | When two parts are equally worth practising |
| 09.11. | Optional "tutor comments" box, treated as reliable | The AI contradicted my tutor about 장 |
| 09.11. | Examples must show the most typical situation; notes explain look-alikes (년도: 도 is not the particle) | 있잖아요 example felt unnatural; 년도 lacked context |
| 09.11. | Continue in new chats in the Claude project; this file is the bridge | The first chat had grown so long that early details were being compressed |
| 09.11. | `messages.create()` plus our own validation instead of `messages.parse()`; errors name the stop reason and output tokens | `parse()` validates inside the call, so an answer cut off mid-JSON crashed before the stop reason was checked |
| 09.11. | Output limit stays at 16,000 tokens until a failure shows the cause | Raising it a lot needs streaming; not worth doing on a guess |
| 10.11. | Output limit 32,000 tokens, answer streamed, progress shown on the page; effort left at the default (high) | 27 October notes hit 16,000 with the 9 November prompt. Sonnet 5.5 thinks before answering by default, and thinking counts toward the limit: only about 13,800 characters of cards had arrived. The SDK requires streaming above about 21,000 tokens |
| 10.11. | Compare effort high vs medium now, with a script outside the card database (one run each, identical input, empty grammar list); Claude does the comparison at my request | Saving both as lessons would let the first run's ticked grammar change the second run's input, and put test cards in my deck. One run each: cheap, enough for big differences, but run-to-run variation is not measured |
| 15.11. | Keep effort high | Medium skipped breakdowns, gaps and an example, and made a trivial correction; the minute it saves per lesson is not worth it. One run each, so partly uncertain |
| 15.11. | Prompt: spacing example (쇼핑해요), gap required on every card (in the schema, not only the prompt), look-alikes checked inside sentences | Seen in the effort runs: 쇼핑 해요 not corrected, 생일이 언제예요? without a gap, 년도 never explained. The examples come from the 27 October notes, so the third run can only confirm the fixes; the next new lesson is the real test |
| 08.11. | Roche link: embeddings first (option A), RAG later (option B) only if A is fun; no React rewrite of the app | Concepts transfer to ATLAS; React would take 5 to 8 weeks and break the app |

## 6. Roadmap

1. **Now: use v0.1 for real** with one or two lessons per week.
2. **My part: progress and weak spots page in SQL** (`views/progress.py`).
   Start once some reviews are logged.
3. **Option A: embeddings** (see section 7). Then a decision point.
4. **Option B: RAG**, only if A was fun.
5. **v0.2:** listening practice (Korean text to speech), typing answers.
6. Later: related sentences and easily confused words, look-alike words
   (spelling similarity), online version, nicer design.
7. **Outside the app:** React basics via the official react.dev tutorial in
   early January.

## 7. Embeddings plan (option A, then B)

### Why later, not now

- The grammar list is sent to the AI in full with every lesson. That is
  cheap and reliable while the list has a few hundred entries, and the AI
  itself handles variants (-아요/-어요 vs -어요). Embeddings would add
  complexity without improving this yet.
- Embeddings earn their place when the AI must find **relevant** things in a
  collection too large or too costly to send in full: all my cards, all my
  lesson notes. That is the situation the app grows into, and the situation
  ATLAS is built for.
- Order matters: first the app must be used and stable, otherwise I would be
  building retrieval on data that does not exist yet.

### What an embedding is (short)

A model turns a piece of text into a list of numbers (a vector) so that
texts with similar meaning get similar numbers. "옷장" and "서랍장" end up
close together; "옷장" and "생일" far apart. A vector database (ChromaDB)
stores these vectors and answers "which stored texts are closest to this
one?" quickly. That question is semantic search.

### Option A: what we build

1. **Embed every card** (Korean + English + note) with a multilingual model
   and store the vectors in ChromaDB in `data/chroma/` (ignored by Git), with
   metadata (card id, kind, lesson date).
2. **Keep it in sync**: embed on save, update on edit, remove on delete.
3. **"Related cards"** on the answer side of each card (for example 신다 shows
   입다, 운동화, 구두).
4. **Search by meaning** on My cards: type "clothes" and find 옷장, 요가복.

**My part: the model experiment.** Chroma's default embedding model
(all-MiniLM-L6-v2) was trained on English and is known to work poorly on
other scripts. I compare it with a multilingual model on my own cards: for a
list of pairs I judge as related or unrelated, which model ranks the related
ones higher? This is a small, honest evaluation, close to my thesis work.

**Embedding provider:** Voyage AI (multilingual models; free allowance of
200 million tokens, far beyond what this app needs). Needs its own account
and API key in `secrets.toml`.

### Option B: RAG

RAG (retrieval augmented generation) = find the relevant pieces first, then
give only those to the language model.

1. **Smarter drafting.** Before drafting cards from new notes, retrieve my
   most similar existing cards and send them along. The AI can then avoid
   duplicates, link new words to known ones ("you already have 운동복"), and
   decide which grammar is really new even when the grammar list becomes long.
   This replaces "send the whole list" when the list gets too big.
2. **"Ask my notes" page.** Ask "What did we learn about verbs for wearing?";
   the app retrieves the relevant lesson notes and cards, and Claude answers,
   naming the lesson each point comes from.
3. **Testing where it fails**: questions with no answer in my notes, mixed
   Korean and English questions, very short notes.

### What this teaches for Roche (ATLAS)

Embeddings, choosing and evaluating an embedding model, ChromaDB
(collections, metadata, queries), keeping a vector store in sync with a SQL
database, the RAG pattern (retrieve, build the prompt, cite sources) and its
failure modes. ChromaDB works the same way from Python and JavaScript, so the
concepts carry over.

### Known risks and open points

- Python 3.15 is very new; ChromaDB depends on onnxruntime, which may not
  support it yet. Fallback: a 3.13 environment for the project.
- Korean quality of Voyage's models is described as multilingual, not
  confirmed for Korean specifically. My experiment answers this.
- Embeddings find related **meaning** (신다 / 입다 / 쓰다), not words that
  **look or sound alike** (낫다 / 낮다 / 낳다). Those need a spelling
  comparison (edit distance on jamo), a separate small feature.
- For a few hundred cards ChromaDB is more than needed (a plain list of
  vectors would do). We use it because learning it is the point.

## 8. Open questions

- Ask my tutor: is "있잖아요, 오늘 시간 있어요?" natural, or is 있잖아요 mostly
  used to start telling something ("있잖아요, 저 어제 ...")?
- Ask my tutor: what did "nfj 똑같아요!" refer to?
- Look-alikes (rule 10): 년도 was missed even though it is the rule's own
  example. If the next lessons miss look-alikes too, give the schema its own
  field for it (as was done for gaps), so the model has to consider it on
  every card.
- Ask my tutor: did "구두 = heel" mean heeled shoes? Both runs called it
  wrong (구두 = dress shoes; a shoe's heel is 굽).
- Is a batch size of 15 right? Decide after a week of use.
- Delete `data/korean-backup-before-rerun.db` and
  `data/korean-backup-before-date-fix.db`: the third-run cards are saved and
  the date is fixed.

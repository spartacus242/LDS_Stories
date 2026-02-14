# LDS Doctrine Insights Agent

This project provides a runnable **research assistant/bot** that:

- gathers LDS doctrine and world-context sources (scripture, General Authority talks, historical records, current events, social/technology trends),
- extracts short insight candidates,
- verifies whether quoted text appears in the source,
- cites sources for every card,
- explicitly labels uncertainty when evidence is weak/inconclusive,
- formats output as short, attention-grabbing "Instagram-style" story cards,
- attaches **non-AI image candidates** (from Wikimedia Commons metadata filters).

## Important boundaries

This tool is for **study support**, not for issuing doctrine, prophecy, or official Church interpretations.  
It uses heuristic NLP, and the output must be reviewed by a human before publication.

## What it generates

For each story card, the agent emits:

- headline,
- short narrative paragraph,
- practical action step,
- confidence level,
- explicit uncertainty note,
- citations (title + URL + quote verification status),
- image attribution and license when found.

## Project layout

```text
story_agent/
  agent.py          # Orchestrator
  fetchers.py       # Source loading + URL ingestion
  verifier.py       # Quote verification (exact/close/no match)
  insights.py       # Insight heuristics
  images.py         # Wikimedia non-AI image lookup
  formatter.py      # Instagram-style output formatters
  cli.py            # Command line interface
config/
  sources.example.yaml
tests/
  test_verifier.py
  test_insights.py
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python -m story_agent --config config/sources.example.yaml --output-dir output --max-insights 5
```

Skip image lookup if desired:

```bash
python -m story_agent --config config/sources.example.yaml --no-images
```

## Instagram export bundle

Each run now also writes a social-ready export bundle:

- `output/instagram_<timestamp>/captions/*.txt`
  - one caption file per card
  - includes action step, confidence/uncertainty, source list, and hashtag block
- `output/instagram_<timestamp>/scheduler_square_cards.json`
  - square-card scheduling template (`1080x1080`, `1:1`)
  - references caption file, image metadata, citations, and publish order
- `output/instagram_<timestamp>/hashtags_bank.txt`
  - de-duplicated hashtag bank from all generated cards

## Configure sources

Edit `config/sources.example.yaml`:

```yaml
sources:
  - name: Doctrine and Covenants 1
    url: https://www.churchofjesuschrist.org/study/scriptures/dc-testament/dc/1?lang=eng
    source_type: scripture
    tags: [warning, preparation]

  - name: Example First Presidency Talk
    url: https://www.churchofjesuschrist.org/study/general-conference/2023/10/51nelson?lang=eng
    source_type: general_authority_talk
    author: Russell M. Nelson
    authority_office: First Presidency

  - name: Wikipedia Current Events Portal
    url: https://en.wikipedia.org/wiki/Portal:Current_events
    source_type: current_event
```

## Confidence + uncertainty handling

The verifier returns:

- `high`: exact normalized quote match,
- `medium`: close textual match (possible paraphrase),
- `low`: weak or no match (inconclusive / possible error).

Story cards always include an `uncertainty_note` to avoid overstated claims.

## Non-AI image policy

Image search uses Wikimedia Commons and rejects candidates when metadata suggests:

- AI generation,
- illustration/digital art/cartoon markers,
- non-photographic rendering terms.

Because metadata can be incomplete, the agent flags this as **"probably non-AI"** and requires human review.

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

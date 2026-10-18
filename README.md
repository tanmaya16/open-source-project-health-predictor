# Open-Source Project Health Predictor

A Streamlit MVP that analyzes public GitHub repositories using transparent, rule-based maintenance signals.

> **Important:** This is a rule-based heuristic, not a trained machine-learning model. Its score is not a probability that a repository will become inactive, and it does not predict whether a repository will receive no commits in the next 12 months.

## Features

- Analyze a public GitHub repository using `owner/repository`.
- Display basic repository metadata and recent activity samples.
- Show a transparent maintenance-concern score and explanatory signals.
- Export the analysis as JSON (when available in the app).
- Use a GitHub personal access token locally for higher general API capacity.

## Requirements

- Windows, macOS, or Linux
- Python 3.11 or newer recommended
- Internet connection

## Run on Windows

1. Download or clone this repository.
2. Double-click `run.bat`.
3. Wait for the virtual environment and required packages to be prepared.
4. Open the local Streamlit URL shown in the terminal if it does not open automatically.

The first launch requires internet access to install Python packages.

## Run manually

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

python -m pip install -r requirements.txt
streamlit run app.py
```

## Optional GitHub token

If you hit GitHub API rate limits, you can add a token to a local `.env` file:

```dotenv
GITHUB_TOKEN=your_token_here
```

Never commit `.env`, paste your token into an issue, or share it in screenshots. The application should read the token from the local environment and never display it.

## Project structure

```text
open-source-project-health-predictor/
├── app.py
├── run.bat
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── src/
├── tests/
└── data/
    ├── raw/
    └── processed/
```

## Score interpretation

Lower scores mean fewer concern points under the currently implemented rules. The score is heuristic and should not be interpreted as a probability, a guarantee of project health, or a security assessment.

## Limitations

- GitHub's current repository fields are not historical snapshots.
- Recent API samples are capped and do not represent complete histories or annual totals.
- Contributor samples are not a complete bus-factor calculation.
- API limits and partial endpoint failures can affect available evidence.
- Inactivity does not prove that a project is abandoned or insecure.
- No trained model or validated 12-month inactivity prediction is included in this MVP.

## Development

Run tests with:

```bash
python -m unittest discover -s tests -v
```

## License

No license has been selected. If you publish this repository publicly, choose a license if you want others to have explicit permission to reuse, modify, and distribute the code.

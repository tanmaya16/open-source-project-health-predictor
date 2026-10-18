from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv
from health_scoring import assess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))
API_ROOT = "https://api.github.com"
USER_AGENT = "open-source-project-health-predictor/1.0"

st.set_page_config(page_title="Open-Source Project Health Predictor", page_icon="🧭", layout="wide")
st.title("Open-Source Project Health Predictor")
st.caption("Public GitHub repository · transparent maintenance signals")
st.info(
    "This is a rule-based MVP, not a trained machine-learning model. Its score summarizes observed signals; "
    "it is not a probability that a repository will become inactive."
)


class GitHubAPIError(RuntimeError):
    """Friendly, user-facing GitHub API error."""


def github_get(path: str, token: str = "", params: dict[str, Any] | None = None) -> Any:
    """Make one bounded GitHub REST API request. Never waits for a long rate-limit reset."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(
            path if path.startswith("https://") else f"{API_ROOT}{path}",
            headers=headers,
            params=params,
            timeout=20,
        )
    except requests.RequestException as exc:
        raise GitHubAPIError(f"Network request failed: {exc}") from exc

    if response.status_code in (403, 429):
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        retry_after = response.headers.get("Retry-After")
        message = "GitHub has rate-limited this request."
        if retry_after:
            message += f" Retry-After: {retry_after} seconds."
        elif remaining == "0" and reset:
            try:
                reset_dt = datetime.fromtimestamp(int(reset), tz=timezone.utc)
                message += f" The primary rate limit resets around {reset_dt:%Y-%m-%d %H:%M:%S UTC}."
            except (ValueError, OverflowError, OSError):
                pass
        message += " Stop retrying for now. An optional read-only GitHub token in your local .env can increase the general API limit; secondary limits can still apply. Never share the token."
        raise GitHubAPIError(message)
    if response.status_code == 404:
        raise GitHubAPIError("Repository or endpoint not found. Check the owner/repository spelling and make sure the repository is public.")
    if response.status_code == 401:
        raise GitHubAPIError("GitHub rejected the token. Check the local .env value, or remove the token to use unauthenticated public access.")
    if not response.ok:
        detail = response.text[:220].replace("\n", " ")
        raise GitHubAPIError(f"GitHub returned HTTP {response.status_code}: {detail}")
    try:
        return response.json()
    except ValueError as exc:
        raise GitHubAPIError("GitHub returned a response that was not valid JSON.") from exc



def fetch_optional_list(path: str, token: str, params: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch a secondary endpoint; return an error string instead of losing the whole report."""
    try:
        result = github_get(path, token, params)
        if not isinstance(result, list):
            return [], "GitHub returned an unexpected response format."
        return result, None
    except GitHubAPIError as exc:
        return [], str(exc)


with st.sidebar:
    st.header("Analyze a repository")
    repo_input = st.text_input("Public GitHub repository", value="pallets/flask", placeholder="owner/repository")
    st.caption("Enter a public repository as owner/repository.")
    st.markdown("**Optional authentication**")
    st.caption("For more general API capacity, add GITHUB_TOKEN=... to the local .env file and restart. Never enter or share the token in this app or chat.")
    analyze = st.button("Analyze repository", type="primary", use_container_width=True)

if analyze:
    normalized = repo_input.strip().strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", normalized):
        st.error("Enter a valid repository in owner/repository format, for example: pallets/flask")
        st.stop()

    owner, name = normalized.split("/", 1)
    token = os.getenv("GITHUB_TOKEN", "").strip()
    base = f"/repos/{owner}/{name}"
    with st.spinner("Fetching repository metadata and recent activity from GitHub..."):
        try:
            repo = github_get(base, token)
        except GitHubAPIError as exc:
            st.error(str(exc))
            st.stop()

        # Fetch each activity endpoint independently so a single optional endpoint failure
        # still leaves a useful partial report. No automatic long waits or repeated retries.
        endpoint_specs = [
            ("commits", base + "/commits", {"per_page": 20}),
            ("contributors", base + "/contributors", {"per_page": 30}),
            ("releases", base + "/releases", {"per_page": 10}),
            ("issues", base + "/issues", {"state": "all", "per_page": 30}),
            ("pull_requests", base + "/pulls", {"state": "all", "per_page": 30}),
        ]
        endpoint_data: dict[str, list[dict[str, Any]]] = {}
        endpoint_errors: dict[str, str] = {}
        rate_limited = False
        for endpoint_name, endpoint_path, endpoint_params in endpoint_specs:
            data, error = fetch_optional_list(endpoint_path, token, endpoint_params)
            endpoint_data[endpoint_name] = data
            if error:
                endpoint_errors[endpoint_name] = error
                if "rate-limit" in error.lower() or "rate limited" in error.lower():
                    rate_limited = True
                    break
        if rate_limited:
            for endpoint_name, _, _ in endpoint_specs:
                if endpoint_name not in endpoint_data:
                    endpoint_data[endpoint_name] = []
                    endpoint_errors[endpoint_name] = "Not requested because GitHub rate-limited an earlier request."
        commits = endpoint_data.get("commits", [])
        contributors = endpoint_data.get("contributors", [])
        releases = endpoint_data.get("releases", [])
        issues = endpoint_data.get("issues", [])
        pulls = endpoint_data.get("pull_requests", [])

    result = assess(repo, commits, contributors, releases, issues, pulls)
    generated_at = datetime.now(timezone.utc).isoformat()
    errors = endpoint_errors
    st.session_state["last_report"] = {
        "repository": repo,
        "analysis": result,
        "endpoint_errors": errors,
        "generated_at_utc": generated_at,
        "method": "transparent_rule_based_heuristic_v1",
    }

if "last_report" in st.session_state:
    report = st.session_state["last_report"]
    repo = report["repository"]
    result = report["analysis"]
    details = result["details"]

    st.subheader(repo.get("full_name") or repo.get("html_url") or "Repository analysis")
    if repo.get("html_url"):
        st.markdown(f"[Open repository on GitHub]({repo['html_url']})")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Maintenance concern", f"{result['score']}/100", help="Heuristic concern score, not a probability.")
    c2.metric("Stars", f"{int(repo.get('stargazers_count') or 0):,}")
    c3.metric("Forks", f"{int(repo.get('forks_count') or 0):,}")
    c4.metric("Days since latest push", "Unknown" if details["days_since_latest_push"] is None else details["days_since_latest_push"])
    st.markdown(f"### {result['label']}")
    st.caption("Lower score means fewer concern points under these explicit rules. It does not mean zero risk.")

    st.markdown("#### Why this result was produced")
    # Use Streamlit's static table instead of the canvas-based interactive grid.
    # This avoids confusing canvas artifacts when users copy/export the report text.
    st.table(result["signals"])
    st.progress(result["score"] / 100, text=f"Heuristic concern score: {result['score']} / 100")

    st.markdown("#### Sampled activity (not complete history)")
    st.table([{
        "Language": repo.get("language") or "Unknown",
        "Created": repo.get("created_at"),
        "Last pushed": repo.get("pushed_at"),
        "Archived": bool(repo.get("archived")),
        "Commits sampled (max 20)": details["sampled_commits"],
        "Contributors sampled (max 30)": details["sampled_contributors"],
        "Releases sampled (max 10)": details["sampled_releases"],
        "Issues sampled (max 30, includes PRs before filtering)": details["sampled_issues_excluding_pull_requests"],
        "Pull requests sampled (max 30)": details["sampled_pull_requests"],
    }])

    if report["endpoint_errors"]:
        st.warning("Some activity endpoints could not be read. Treat the score as partial; failed endpoints are not proof of inactivity.")
        with st.expander("Endpoint warnings"):
            for endpoint, message in report["endpoint_errors"].items():
                st.write(f"**{endpoint}:** {message}")

    st.markdown("#### Limitations")
    st.markdown(
        "- GitHub's current `pushed_at` field is not a historical snapshot.\n"
        "- API samples are capped and do not represent complete histories or annual totals.\n"
        "- Contributor sample size is not a complete bus-factor calculation.\n"
        "- Inactivity does not prove that a project is abandoned, unsafe, or insecure.\n"
        "- This version has no trained model and does not estimate the probability of no commits in the next 12 months."
    )
    st.caption(f"Report generated (UTC): {report['generated_at_utc']}")
    st.download_button(
        "Download analysis report (JSON)",
        data=json.dumps(report, indent=2, ensure_ascii=False),
        file_name=f"{repo.get('full_name', 'repository').replace('/', '_')}_health_report.json",
        mime="application/json",
        use_container_width=True,
    )
else:
    st.markdown("### Start with a public repository")
    st.write("The repository field is pre-filled with `pallets/flask`. Select **Analyze repository** in the sidebar to begin.")
    st.caption("The first analysis may use several GitHub API requests. If rate-limited, wait until the displayed reset time or configure an optional token locally.")

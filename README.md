# AI Code Reviewer

A Python learning project that reviews GitHub pull-request diffs, retrieves related
reviews from Supabase, and posts one combined Markdown comment to the PR.
Run it locally or automatically through GitHub Actions.

## How it works

```text
Fetch PR files
  → skip excluded files and files without a text patch
  → embed the current filename and diff
  → retrieve up to 3 reviews for the same repository and filename
  → generate a review with the retrieved context
  → embed and save the filename, diff, and new review
  → combine all new file reviews into one GitHub comment
```

Reviews use `gpt-4o-mini` through the Responses API, capped at 600 output tokens
per file. Embeddings use `text-embedding-3-small` with its default 1,536 dimensions.
These settings currently live in `ai_code_reviewer.py`.

Each reviewed file makes three OpenAI requests: a search embedding, a review, and
a storage embedding. These incur API usage charges. Retrieved history is context,
not verified evidence; human review is still necessary.

## Files

| File | Purpose |
| --- | --- |
| `ai_code_reviewer.py` | CLI, GitHub fetching, AI reviews, retrieval, storage, and comments |
| `check_supabase_connection.py` | Small database connectivity check |
| `check_github_connection.py` | Read-only learning example fetching PR #2 in this repository |
| `check_openai_connection.py` | Small, billable OpenAI connection check |
| `embeddings.py` | Standalone embedding learning example; the reviewer uses its own helper |
| `requirements.txt` | Python dependencies |
| `.env.example` | Placeholder configuration; contains no credentials |
| `supabase/setup.sql` | Fresh-project schema and retrieval function |
| `.github/workflows/ai-review.yml` | Automated PR review workflow |

## Local setup

Use Python 3.13 to match the workflow. You need a GitHub repository and PR,
an OpenAI API key with API access and billing, and a Supabase project.

```bash
git clone https://github.com/isaikirany/ai-code-reviewer.git
cd ai-code-reviewer
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell.
Dependencies are currently unpinned; this is not a reproducible lockfile setup.

If you do not already have a `.env`, copy `.env.example` to `.env` and replace
the placeholders. Keep an existing `.env` rather than overwriting it.

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Authentication for review and embedding requests |
| `GITHUB_TOKEN` | Local GitHub token with access to the target repository |
| `SUPABASE_URL` | URL of the project containing the review table |
| `SUPABASE_KEY` | Backend secret key for the same Supabase project |

For local GitHub access, use a fine-grained token restricted to the target
repository with **Pull requests: Read and write**. Reading alone is insufficient
to post comments. See [GitHub token setup](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

The script loads `.env` beside itself with `override=True`: file values take
precedence over existing environment variables. Git ignores `.env`; never commit
real keys or paste them into issue reports.

## Supabase setup

For a **new project**, run [supabase/setup.sql](supabase/setup.sql) in the Supabase
SQL Editor. The script creates the vector extension, `public.rag_content`, and
`public.match_file_reviews`. It enables RLS and grants backend access through
`service_role`, while denying public client access to these objects.

Use your own operator-controlled Supabase secret key locally and in Actions
secrets. It bypasses RLS and must not be shipped to other users. Each person
installing this project supplies their own credentials. See
[Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys).

If your database already has the table and function from the manual tutorial,
do not rerun the fresh-project script: compare its definitions with your existing
objects instead. The script intentionally fails if the table exists, rather than
replacing your data or assuming its schema matches. It has not been applied to
your existing database by this documentation change.

Ensure `public` is exposed through your project's Supabase Data API. Verify access:

```bash
python check_supabase_connection.py
```

An empty result is valid: the table may have no rows yet.

### Stored records and retrieval

| Column | Stored value |
| --- | --- |
| `id` | `owner/repo/pulls/3/files/path/to/file.py` |
| `document_id` | `owner/repo/pulls/3` |
| `context` | Filename, diff, and generated review text |
| `embedding` | 1,536-number embedding of that context |
| `user_id` | PR author's numeric GitHub ID |
| `username` | PR author's GitHub login |
| `document_type` | `pr_chunk` |

One row represents one file in one PR. Upserting the same ID replaces that row;
it does not preserve every run or commit. The schema currently uses a PostgreSQL
`integer` for the author ID, which has a 32-bit limit.

Retrieval filters to the exact repository and filename, excludes the current PR,
then ranks matches by cosine distance. It returns at most three records, with no
minimum similarity threshold. It does not check PR dates or merge status. A file
rename does not retrieve history stored under its former path. The old tutorial
function `match_documents_by_document_type` is not used by this implementation.

Repository renames also change the stored repository identifier. Reviews saved
under an old name are not retrieved under the new name unless their IDs and
document IDs are migrated. Existing history is not migrated automatically.

## Run a review

```bash
python ai_code_reviewer.py --help
python ai_code_reviewer.py --repo OWNER/REPOSITORY --pr 3
```

`--help` exits before credentials are loaded. An actual review reads GitHub data,
sends diffs and selected history to OpenAI, stores results in Supabase, and posts
a real PR comment. Every rerun posts another comment.

Exclude files using quoted shell-style patterns:

```bash
python ai_code_reviewer.py --repo OWNER/REPOSITORY --pr 3 \
  --exclude "*.lock" "*.png" "requirements.txt"
```

The defaults are `*.lock`, `*.png`, `*.jpg`, `*.jpeg`, `*.gif`, and `*.svg`.
Explicit patterns replace the defaults. `--exclude` with no patterns disables
exclusions. Patterns use Python `fnmatch`, not Git's ignore rules.

To verify exclusions, exclude every changed file in a small PR. The script should
print `No reviews to post.` without making OpenAI requests or storing reviews.

## GitHub Actions

The workflow runs on PR `opened`, `synchronize` (new commits), and `reopened`
events for branches in the same repository. Fork PRs are skipped.

1. Make sure `ai_code_reviewer.py` and `requirements.txt` exist on the base branch
   before the first automated review.
2. In **Settings → Secrets and variables → Actions**, add `OPENAI_API_KEY`,
   `SUPABASE_URL`, and `SUPABASE_KEY` as repository secrets.
3. Add `.github/workflows/ai-review.yml` through a PR and verify its check before
   merging it into the default branch.
4. Open a practice PR. Inspect **Checks → AI Code Review → review** and confirm
   the generated comment and saved database row.

GitHub supplies the workflow's `GITHUB_TOKEN` automatically. Its permissions are
`contents: read` and `pull-requests: write`; do not upload your personal token.
No `.env` file is needed on the runner. The job uses Python 3.13 on Ubuntu and
has a 10-minute timeout.

Checkout uses the PR's **base SHA**, so Python and dependency installation run
from the base code. Proposed changes are fetched as diff text through the API.
Changes to the reviewer therefore take effect for later PR runs after they reach
the base branch. This is not a complete isolation boundary: same-repository
contributors can also propose workflow changes, so this setup assumes trusted
contributors. Do not switch to executing fork code with repository secrets.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `ModuleNotFoundError` | Activate `.venv`, then install `requirements.txt` with `python -m pip` |
| Supabase `401 Invalid API key` | URL and key must belong to the same project; save `.env` after updating |
| GitHub comment `403` | Local token needs PR write permission; Actions needs `pull-requests: write` |
| Push rejected for missing `workflow` scope | Git's push credential needs workflow-edit permission; editing `.env` does not update Git credentials |
| `match_file_reviews` not found | Confirm the function is installed in `public` and accessible through the Data API |
| Supabase permission error | Check table/function grants and the role associated with the key |
| Vector dimension error | Both stored and query embeddings must use the configured 1,536-dimensional model |
| `Retrieved 0 previous review(s)` | Expected if only the current PR has a stored record for that file |
| Actions cannot find reviewer/requirements | These files must exist at the checked-out base commit |
| OpenAI authentication/quota error | Check the API key, API billing, and available quota |

The workflow-level `try/except` prints `Review failed: ...` and exits with code 1.
Configuration errors before that block can still show a traceback. A failure does
not roll back rows saved earlier in the run; a timeout can also leave partial data.

## Verification and limitations

Check syntax and CLI parsing without API calls:

```bash
python -m py_compile ai_code_reviewer.py
python ai_code_reviewer.py --help
```

For an integration check, review one PR, then another changing the same file.
The second should retrieve the first PR's saved record. Verify storage with:

```sql
select id, username, context, vector_dims(embedding) as dimensions
from public.rag_content
where document_id = 'OWNER/REPOSITORY/pulls/3';
```

Current limitations:

- No automated test suite or fresh-database CI test is included.
- Reviews use GitHub patches, not complete files or repository-wide analysis.
  Missing patches are skipped; truncated patches may give incomplete context.
- Large diffs/history can exceed model limits, and combined comments can exceed
  GitHub's size limit. There is no chunking, batching, or custom rate-limit policy.
- The script does not run tests or decide whether a PR can merge. A successful
  check means execution succeeded, not that the proposed code is correct.
- AI output can be generic or wrong, and stored reviews can carry those errors
  into later prompts. Prompt instructions do not guarantee resistance to injection.
- No comment deduplication or workflow concurrency control exists. Overlapping
  runs can post duplicate comments and overwrite the same saved row.
- Diffs and reviews are sent to external services, and review text appears in
  terminal/Actions logs. Use only repositories whose data you may process there.

Before sharing changes, run the syntax/help checks and inspect the staged diff
for credentials. Use a dedicated practice PR for tests that post comments.
No license has been selected yet; add an explicit license before advertising
the project as open source.

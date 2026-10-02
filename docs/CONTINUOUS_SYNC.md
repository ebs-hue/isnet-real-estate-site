# Authorized continuous data publication

Collection and model generation run in private repository `ebs-hue/isnet-real-estate`. Publication runs in `ebs-hue/isnet-real-estate-site`.

The old public workflow could not anonymously download private source files. Daily publication is now assigned to the scheduled ChatGPT task **עדכון מחירוני הדירות**, using the authorized GitHub connector. It does not require exposing the private repository or writing access tokens into source code.

## Each iteration

1. Read current branches for both repositories. Inspect collection/model workflow health; if builds are in progress, defer publication. Never retry a board in `requires_review` automatically.
2. Pin the engine's current commit SHA. Read `scripts/prepare-pricebook-sync.py` from the current public repository, then download all ten files in its `MAPPING` through GitHub `fetch_file` at that pinned SHA to a scratch input directory. A missing mandatory file cancels the publication batch.
3. Obtain current city HTML and all QA dependencies from the public repository into a scratch site checkout. Keep city pages unchanged. Run the preparation script with `--source-dir`, `--site-dir`, `--engine-commit`.
4. Inventory is field-allowlisted. Quarterly records retain exact-city filtering, date normalization and conservative parcel/address evidence. Model fallback labels must remain separate from closed-sale prices.
5. Install the public repository's pinned Node dependency lockfile outside the public artifact directory; run `NODE_PATH=<qa-node-modules> node scripts/qa-pricebooks.cjs`. If QA fails, do not publish a partial batch or alter expected results just to make it pass; diagnose and report.
6. Compare prepared data to current public data. If identical, do not commit. Otherwise create one atomic GitHub tree/commit with changed approved data paths only, based on the latest site main head. If main advanced, reread affected files and resolve before retrying. Never force-push.
7. Verify `Publish priceboard` completes successfully. Report updates or material failures in Hebrew; no notifications for no-change runs. No email/Slack messages.

## Limits

This is a scheduled agent task using the connector, not a credential-backed cross-repository GitHub Actions bridge. Its first unattended execution still needs verification. Connector availability, task execution and validation failures can delay publication. The engine schedule continues independently.

The quarter files are explicitly Q3 2026. They must not be relabeled as the current quarter after time advances; adding a new quarter is a separate dataset update.

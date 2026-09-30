"""Main entry point for the analyzer."""

import argparse
import sys
from typing import Optional

from .config import validate_config, config, Config
from .firebase_client import initialize_firebase
from .gemini_client import test_connection
from .processors.batch import AnalysisAbortedError, BatchProcessor, run_all_analysis


def run_batch_mode(args):
    """Run batch mode analysis (Gemini Batch API).

    Handles the 3-phase workflow: prepare -> submit -> poll -> import.
    With --loop, repeats until all videos are analyzed.
    """
    phase = args.phase
    analysis_type = args.type

    # Handle 'status' phase (no analysis type needed)
    if phase == "status":
        _show_batch_status()
        return

    # For 'all' analysis type, run both sequentially
    if analysis_type == "all":
        for atype in ["thumbnail", "title_description"]:
            print(f"\n{'#' * 60}")
            print(f"  BATCH: {atype.upper()}")
            print(f"{'#' * 60}")
            _run_batch_loop(phase, atype, args)
    else:
        _run_batch_loop(phase, analysis_type, args)


class BatchRunError(RuntimeError):
    """A batch run stopped before completion. No new job was submitted."""


def _run_batch_loop(phase: str, analysis_type: str, args):
    """Run batch phases, looping if --loop is set."""
    if phase != "all":
        _run_batch_phase(phase, analysis_type, args)
        return

    if not args.loop:
        result = _run_batch_phase_with_stats(analysis_type, args)
        if result is not None:
            print(f"\n  Batch complete: {result['imported']} imported")
        return

    batch_num = 0
    total_processed = 0

    while True:
        batch_num += 1
        print(f"\n{'=' * 60}")
        print(f"  BATCH JOB #{batch_num}  |  {total_processed:,} processed so far")
        print(f"{'=' * 60}")

        result = _run_batch_phase_with_stats(analysis_type, args)

        if result is None:
            # No requests to process — all done
            break

        imported = result["imported"]
        total_processed += imported
        print(f"\n  Batch #{batch_num} complete: {imported} imported  |  Running total: {total_processed:,}")

        if imported == 0:
            # No progress: the next prepare would pick the same videos again
            print("\n  Nothing was imported from this batch. Stopping loop to avoid resubmitting the same videos.")
            break

    print(f"\n{'=' * 60}")
    print("  ALL BATCHES COMPLETE")
    print(f"  Total batches: {batch_num}")
    print(f"  Total imported: {total_processed:,}")
    print(f"{'=' * 60}")


def _ensure_no_blocking_job(analysis_type: str) -> None:
    """Raise BatchRunError if an in-flight or un-imported job exists for this type."""
    from .batch_api.submit import ABANDON_HINT, find_blocking_job

    kind, job = find_blocking_job(analysis_type)
    if kind:
        raise BatchRunError(
            f"{kind} {analysis_type} job {job['jobName']} ({job.get('state')}) must be polled/imported first "
            "(use --phase all to resume it, or --phase poll / --phase import). "
            + ABANDON_HINT.format(job_name=job["jobName"])
        )


def _poll_and_import(analysis_type: str, job_name: str, args) -> dict:
    """Poll a job to completion and import its results. Raises if it did not succeed."""
    from .batch_api import poll_and_update, import_batch_results
    from .batch_api.client import IMPORTABLE_STATES

    result = poll_and_update(
        analysis_type=analysis_type,
        poll_interval=args.poll_interval,
        job_name=job_name,
    )
    state = result.get("state")
    if result.get("abandoned"):
        raise BatchRunError(
            f"Job {job_name} no longer exists in the Gemini API and was marked abandoned. "
            "Re-run to prepare a new batch."
        )
    if state not in IMPORTABLE_STATES:
        raise BatchRunError(f"Job {job_name} did not succeed (state: {state}). Re-run to resume or start a new batch.")

    stats = import_batch_results(analysis_type=analysis_type, job_name=job_name)
    return {"imported": stats.get("imported", 0)}


def _run_batch_phase_with_stats(analysis_type: str, args) -> Optional[dict]:
    """Run all batch phases and return {"imported": n}. Returns None if no work to do.

    An existing un-imported or in-flight job is finished first instead of preparing
    new work. Errors while checking for, polling or importing a job propagate so that
    a new (duplicate, billed) job is never submitted after a failed resume.
    """
    from .batch_api import prepare_batch_requests, submit_batch
    from .batch_api.submit import ABANDON_HINT, find_blocking_job

    kind, existing = find_blocking_job(analysis_type)
    if kind:
        label = "unimported finished" if kind == "unimported" else "active"
        print(f"\n  Found {label} job: {existing['jobName']} ({existing.get('state')})")
        print(f"  {ABANDON_HINT.format(job_name=existing['jobName'])}")
        return _poll_and_import(analysis_type, existing["jobName"], args)

    # No existing jobs — prepare new batch
    jsonl_path, count = prepare_batch_requests(
        analysis_type=analysis_type,
        channel_id=args.channel,
        batch_size=args.batch_size,
    )
    if count == 0:
        return None

    job_record = submit_batch(
        jsonl_path=jsonl_path,
        analysis_type=analysis_type,
        request_count=count,
    )
    return _poll_and_import(analysis_type, job_record["jobName"], args)


def _run_batch_phase(phase: str, analysis_type: str, args):
    """Execute a single batch phase (prepare, submit, poll or import) for an analysis type."""
    from .batch_api import (
        prepare_batch_requests,
        submit_batch,
        poll_and_update,
        import_batch_results,
    )

    if phase == "prepare":
        _ensure_no_blocking_job(analysis_type)
        prepare_batch_requests(
            analysis_type=analysis_type,
            channel_id=args.channel,
            batch_size=args.batch_size,
        )

    elif phase == "submit":
        import glob
        import os
        from .firebase_client import get_batch_jobs_by_jsonl_path

        # Find the most recent prepared JSONL
        batch_dir = os.path.join(config.PROJECT_ROOT, "data", "batch")
        pattern = os.path.join(batch_dir, f"batch_{analysis_type}_*.jsonl")
        files = sorted(glob.glob(pattern), reverse=True)
        if not files:
            print(f"No prepared JSONL file found for {analysis_type}")
            return
        jsonl_path = files[0]

        submitted = get_batch_jobs_by_jsonl_path(jsonl_path)
        if submitted:
            raise BatchRunError(
                f"{jsonl_path} was already submitted as {submitted[0]['jobName']}. "
                "Run --phase prepare to build a new file."
            )
        _ensure_no_blocking_job(analysis_type)

        with open(jsonl_path) as f:
            count = sum(1 for _ in f)
        print(f"Using prepared file: {jsonl_path} ({count} requests)")

        submit_batch(
            jsonl_path=jsonl_path,
            analysis_type=analysis_type,
            request_count=count,
            job_name=args.job_name,
        )

    elif phase == "poll":
        result = poll_and_update(
            analysis_type=analysis_type,
            poll_interval=args.poll_interval,
            job_name=args.job_name,
        )
        from .batch_api.client import IMPORTABLE_STATES

        if result and result.get("state") not in IMPORTABLE_STATES:
            print(f"Job did not succeed (state: {result.get('state')}).")

    elif phase == "import":
        import_batch_results(
            analysis_type=analysis_type,
            job_name=args.job_name,
        )


def _show_batch_status():
    """Show status of all batch jobs."""
    from .firebase_client import list_all_batch_jobs
    from .batch_api.client import list_batch_jobs as list_api_jobs

    print("\n" + "=" * 70)
    print("  BATCH JOB STATUS")
    print("=" * 70)

    # Show Firestore-tracked jobs
    jobs = list_all_batch_jobs(limit=20)
    if not jobs:
        print("\n  No batch jobs found in Firestore.")
    else:
        print(f"\n  {'Job Name':<35} {'Type':<20} {'State':<25} {'Requests':<10} {'Imported'}")
        print(f"  {'-' * 35} {'-' * 20} {'-' * 25} {'-' * 10} {'-' * 8}")
        for job in jobs:
            name = job.get("jobName", job.get("id", "?"))
            # Truncate long names
            if len(name) > 33:
                name = "..." + name[-30:]
            atype = job.get("analysisType", "?")
            state = job.get("state", "?")
            count = job.get("requestCount", "?")
            imported = "Yes" if job.get("importedAt") else ("Abandoned" if job.get("abandonedAt") else "No")
            print(f"  {name:<35} {atype:<20} {state:<25} {str(count):<10} {imported}")

    # Also check the API for any jobs not tracked
    print("\n  Checking Gemini API for active jobs...")
    try:
        api_jobs = list_api_jobs(limit=10)
        from .batch_api.client import _state_str, COMPLETED_STATES

        active = [j for j in api_jobs if _state_str(j.state) not in COMPLETED_STATES]
        if active:
            print(f"\n  {len(active)} active job(s) in Gemini API:")
            for j in active:
                print(f"    {j.name}: {j.state}")
        else:
            print("  No active jobs in Gemini API.")
    except Exception as e:
        print(f"  Could not check API: {e}")

    print()


def _abandon_job(job_name: str) -> None:
    """Mark a batch job abandoned so it no longer blocks prepare/submit (--abandon-job)."""
    from .batch_api.submit import abandon_job

    try:
        record = abandon_job(job_name)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    print(
        f"\nMarked {record.get('analysisType', '?')} job {record.get('jobName', job_name)} "
        f"({record.get('state', '?')}) as abandoned. It no longer blocks new batches."
    )
    if record.get("importedAt"):
        print("  Note: this job had already been imported.")


def _get_type_description(analysis_type: str) -> str:
    """Get a human-readable description for an analysis type."""
    if analysis_type == "thumbnail":
        return "thumbnail (vision, ~109 Gemini fields)"
    elif analysis_type == "title_description":
        return "title_description (hybrid: 75 Gemini + 59 local fields)"
    else:
        return "all (thumbnail + title_description)"


def _print_config_summary(args):
    """Print a structured config summary after validation."""
    from .firebase_client import get_all_channels, get_all_channels_unfiltered

    print("\n" + "-" * 60)

    # Mode
    if args.mode == "batch":
        print("  Mode:            BATCH (50% cost savings)")
    else:
        print("  Mode:            SYNC (per-video API calls)")

    # Analysis type
    print(f"  Analysis type:   {_get_type_description(args.type)}")

    # Channel filter
    if args.channel:
        print(f"  Channel filter:  {args.channel}")
    else:
        try:
            enabled = get_all_channels()
            total = get_all_channels_unfiltered()
            print(f"  Channels:        {len(enabled)} enabled / {len(total)} total")
        except Exception:
            print("  Channels:        All channels")

    # Model
    print(f"  Gemini model:    {config.GEMINI_MODEL}")

    # Batch-specific info
    if args.mode == "batch":
        print(f"  Batch size:      {args.batch_size:,} max requests/job")
        phases = args.phase.upper()
        if phases == "ALL":
            phases = "PREPARE -> SUBMIT -> POLL -> IMPORT"
        print(f"\n  Phase: {phases}")

    print("-" * 60)


def _run_sync_mode(args):
    """Run sync (per-video) analysis."""
    if args.channel:
        # Process single channel
        types = ["thumbnail", "title_description"] if args.type == "all" else [args.type]
        for analysis_type in types:
            print(f"\nProcessing {analysis_type} analysis for channel {args.channel}...")
            processor = BatchProcessor(analysis_type)
            stats = processor.process_channel(args.channel, limit=args.limit)
            print(f"Completed: {stats['successful']} successful, {stats['failed']} failed")
    elif args.type == "all":
        run_all_analysis(limit_per_channel=args.limit)
    else:
        BatchProcessor(args.type).process_all_channels(limit=args.limit)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="YouTube Intelligence System - AI Analysis")
    parser.add_argument(
        "--type",
        "-t",
        choices=["all", "thumbnail", "title_description"],
        default="all",
        help="Type of analysis to run (thumbnail=vision, title_description=combined text)",
    )
    parser.add_argument("--limit", "-l", type=int, default=None, help="Limit videos per channel")
    parser.add_argument("--channel", "-c", type=str, default=None, help="Process only this channel ID")
    parser.add_argument("--validate", action="store_true", help="Only validate configuration and connections")

    # Batch mode arguments
    parser.add_argument(
        "--mode",
        "-m",
        choices=["sync", "batch"],
        default="sync",
        help="Processing mode: sync (default, per-video) or batch (Gemini Batch API, 50%% cost savings)",
    )
    parser.add_argument(
        "--phase",
        choices=["all", "prepare", "submit", "poll", "import", "status"],
        default="all",
        help="Batch phase to run (default: all phases sequentially)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=Config.BATCH_MAX_REQUESTS,
        help=f"Maximum requests per batch job (default: {Config.BATCH_MAX_REQUESTS} for Tier 1, use 50000 for Tier 2+)",
    )
    parser.add_argument(
        "--poll-interval", type=int, default=None, help="Seconds between poll checks (default: from config/60s)"
    )
    parser.add_argument("--job-name", type=str, default=None, help="Specific batch job name to poll/import")
    parser.add_argument(
        "--loop", action="store_true", help="Loop batch jobs until all videos are analyzed (batch mode only)"
    )
    parser.add_argument(
        "--abandon-job",
        metavar="JOB_NAME",
        default=None,
        help="Mark a batch job (e.g. batches/abc123) as abandoned so it stops blocking new batches (batch mode only)",
    )

    args = parser.parse_args()
    if args.abandon_job and args.mode != "batch":
        parser.error("--abandon-job requires --mode batch")

    # Validate channel ID format if provided
    if args.channel:
        # YouTube channel IDs start with UC and are 24 characters long
        if not args.channel.startswith("UC") or len(args.channel) != 24:
            print(f"\nError: Invalid channel ID format: {args.channel}")
            print("Channel IDs should start with 'UC' and be 24 characters long.")
            print("Example: UCxxxxxxxxxxxxxxxxxxxxxxx")
            sys.exit(1)

    # Validate configuration
    print("\n" + "=" * 60)
    print("  YouTube Intelligence System - Phase 2: AI Analysis")
    print("=" * 60 + "\n")

    print("Validating configuration...")
    if not validate_config():
        print("\nConfiguration validation failed. Please check your .env file.")
        sys.exit(1)
    Config.load()
    print("Configuration OK")

    # Initialize Firebase
    print("Initializing Firebase...")
    initialize_firebase()
    print("Firebase connected")

    if args.abandon_job:
        _abandon_job(args.abandon_job)
        return

    # For batch status, skip Gemini connection test (Config already loaded above)
    if args.mode == "batch" and args.phase == "status":
        _show_batch_status()
        return

    # Test Gemini connection (skip for batch import phase — it just reads files)
    if not (args.mode == "batch" and args.phase == "import"):
        print("Testing Gemini API connection...")
        if not test_connection():
            print("\nGemini API connection failed. Please check your GOOGLE_API_KEY.")
            sys.exit(1)
        print(f"Gemini API connected (model: {config.GEMINI_MODEL})")

    if args.validate:
        print("\nValidation complete. All connections OK!")
        sys.exit(0)

    # Config summary
    _print_config_summary(args)

    if args.mode == "batch":
        from .batch_api.import_results import BatchImportError

        try:
            run_batch_mode(args)
        except (BatchRunError, BatchImportError) as e:
            print(f"\nBatch run aborted: {e}")
            sys.exit(1)
    else:
        try:
            _run_sync_mode(args)
        except AnalysisAbortedError as e:
            print(f"\nAnalysis aborted: {e}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("  Analysis Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

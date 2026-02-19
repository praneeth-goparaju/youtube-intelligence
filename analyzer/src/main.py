"""Main entry point for the analyzer."""

import argparse
import sys

from .config import validate_config, config, Config
from .firebase_client import initialize_firebase
from .gemini_client import test_connection
from .processors.batch import BatchProcessor, run_all_analysis


def run_batch_mode(args):
    """Run batch mode analysis (Gemini Batch API).

    Handles the 3-phase workflow: prepare -> submit -> poll -> import.
    With --loop, repeats until all videos are analyzed.
    """
    phase = args.phase
    analysis_type = args.type

    # Handle 'status' phase (no analysis type needed)
    if phase == 'status':
        _show_batch_status()
        return

    # For 'all' analysis type, run both sequentially
    if analysis_type == 'all':
        for atype in ['thumbnail', 'title_description']:
            print(f"\n{'#'*60}")
            print(f"  BATCH: {atype.upper()}")
            print(f"{'#'*60}")
            _run_batch_loop(phase, atype, args)
    else:
        _run_batch_loop(phase, analysis_type, args)


def _run_batch_loop(phase: str, analysis_type: str, args):
    """Run batch phases, looping if --loop is set."""
    if not args.loop or phase != 'all':
        _run_batch_phase(phase, analysis_type, args)
        return

    batch_num = 0
    total_processed = 0

    while True:
        batch_num += 1
        print(f"\n{'='*60}")
        print(f"  BATCH JOB #{batch_num}  |  {total_processed:,} processed so far")
        print(f"{'='*60}")

        result = _run_batch_phase_with_stats(analysis_type, args)

        if result is None:
            # No requests to process — all done
            break

        if not result.get('success'):
            print(f"\n  Batch #{batch_num} failed. Stopping loop.")
            break

        imported = result.get('imported', 0)
        total_processed += imported
        print(f"\n  Batch #{batch_num} complete: {imported} imported  |  Running total: {total_processed:,}")

    print(f"\n{'='*60}")
    print(f"  ALL BATCHES COMPLETE")
    print(f"  Total batches: {batch_num}")
    print(f"  Total imported: {total_processed:,}")
    print(f"{'='*60}")


def _run_batch_phase_with_stats(analysis_type: str, args) -> dict:
    """Run all batch phases and return stats. Returns None if no work to do.

    First checks for any succeeded-but-not-imported jobs and imports them
    before preparing new work (avoids duplicate submissions).
    """
    from .batch_api import (
        prepare_batch_requests,
        submit_batch,
        poll_and_update,
        import_batch_results,
    )
    from .firebase_client import get_latest_batch_job

    # Check for existing jobs before preparing new work
    try:
        # Check for unimported succeeded jobs first
        existing = get_latest_batch_job(analysis_type, state='JOB_STATE_SUCCEEDED')
        if existing and not existing.get('importedAt'):
            job_name = existing['jobName']
            print(f"\n  Found unimported succeeded job: {job_name}")
            stats = import_batch_results(
                analysis_type=analysis_type,
                job_name=job_name,
            )
            return {'success': True, 'imported': stats.get('imported', 0)}

        # Check for active jobs that need polling
        for state in ('JOB_STATE_RUNNING', 'JOB_STATE_PENDING', 'JOB_STATE_QUEUED'):
            active = get_latest_batch_job(analysis_type, state=state)
            if active:
                job_name = active['jobName']
                print(f"\n  Found active job: {job_name} ({state})")
                result = poll_and_update(
                    analysis_type=analysis_type,
                    poll_interval=args.poll_interval,
                    job_name=job_name,
                )
                if not result or result.get('state') != 'JOB_STATE_SUCCEEDED':
                    return {'success': False}
                stats = import_batch_results(
                    analysis_type=analysis_type,
                    job_name=job_name,
                )
                return {'success': True, 'imported': stats.get('imported', 0)}
    except Exception as e:
        print(f"  Could not check existing jobs: {e}")
        print(f"  Proceeding with new batch...")

    # No existing jobs — prepare new batch
    jsonl_path, count = prepare_batch_requests(
        analysis_type=analysis_type,
        channel_id=args.channel,
        batch_size=args.batch_size,
    )
    if count == 0:
        return None

    # Submit
    job_record = submit_batch(
        jsonl_path=jsonl_path,
        analysis_type=analysis_type,
        request_count=count,
    )
    job_name = job_record.get('jobName')

    # Poll
    result = poll_and_update(
        analysis_type=analysis_type,
        poll_interval=args.poll_interval,
        job_name=job_name,
    )
    if not result or result.get('state') != 'JOB_STATE_SUCCEEDED':
        return {'success': False}

    # Import
    stats = import_batch_results(
        analysis_type=analysis_type,
        job_name=job_name,
    )

    return {'success': True, 'imported': stats.get('imported', 0)}


def _run_batch_phase(phase: str, analysis_type: str, args):
    """Execute a specific batch phase for an analysis type."""
    from .batch_api import (
        prepare_batch_requests,
        submit_batch,
        poll_and_update,
        import_batch_results,
    )

    # Track job name across phases so poll/import target the correct job
    active_job_name = args.job_name

    if phase in ('all', 'prepare'):
        jsonl_path, count = prepare_batch_requests(
            analysis_type=analysis_type,
            channel_id=args.channel,
            batch_size=args.batch_size,
        )
        if phase == 'prepare' or count == 0:
            if phase == 'all' and count == 0:
                print("No requests to submit — skipping remaining phases.")
            return

    if phase in ('all', 'submit'):
        if phase == 'submit':
            # Need to find the most recent prepared JSONL
            import os
            import glob
            batch_dir = os.path.join(config.PROJECT_ROOT, 'data', 'batch')
            pattern = os.path.join(batch_dir, f"batch_{analysis_type}_*.jsonl")
            files = sorted(glob.glob(pattern), reverse=True)
            if not files:
                print(f"No prepared JSONL file found for {analysis_type}")
                return
            jsonl_path = files[0]
            # Count lines
            with open(jsonl_path) as f:
                count = sum(1 for _ in f)
            print(f"Using prepared file: {jsonl_path} ({count} requests)")

        job_record = submit_batch(
            jsonl_path=jsonl_path,
            analysis_type=analysis_type,
            request_count=count,
            job_name=active_job_name,
        )
        # Use the actual job name from submit for subsequent phases
        if not active_job_name:
            active_job_name = job_record.get('jobName')
        if phase == 'submit':
            return

    if phase in ('all', 'poll'):
        result = poll_and_update(
            analysis_type=analysis_type,
            poll_interval=args.poll_interval,
            job_name=active_job_name,
        )
        if not result:
            return
        state = result.get('state', '')
        if state != 'JOB_STATE_SUCCEEDED':
            print(f"Job did not succeed (state: {state}). Stopping.")
            return
        if phase == 'poll':
            return

    if phase in ('all', 'import'):
        import_batch_results(
            analysis_type=analysis_type,
            job_name=active_job_name,
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
        print(f"  {'-'*35} {'-'*20} {'-'*25} {'-'*10} {'-'*8}")
        for job in jobs:
            name = job.get('jobName', job.get('id', '?'))
            # Truncate long names
            if len(name) > 33:
                name = '...' + name[-30:]
            atype = job.get('analysisType', '?')
            state = job.get('state', '?')
            count = job.get('requestCount', '?')
            imported = 'Yes' if job.get('importedAt') else 'No'
            print(f"  {name:<35} {atype:<20} {state:<25} {str(count):<10} {imported}")

    # Also check the API for any jobs not tracked
    print("\n  Checking Gemini API for active jobs...")
    try:
        api_jobs = list_api_jobs(limit=10)
        from .batch_api.client import _state_str
        active = [j for j in api_jobs if _state_str(j.state) not in {
            'JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED'
        }]
        if active:
            print(f"\n  {len(active)} active job(s) in Gemini API:")
            for j in active:
                print(f"    {j.name}: {j.state}")
        else:
            print("  No active jobs in Gemini API.")
    except Exception as e:
        print(f"  Could not check API: {e}")

    print()


def _get_type_description(analysis_type: str) -> str:
    """Get a human-readable description for an analysis type."""
    if analysis_type == 'thumbnail':
        return 'thumbnail (vision, ~109 Gemini fields)'
    elif analysis_type == 'title_description':
        return 'title_description (hybrid: 75 Gemini + 59 local fields)'
    else:
        return 'all (thumbnail + title_description)'


def _print_config_summary(args):
    """Print a structured config summary after validation."""
    from .firebase_client import get_all_channels, get_all_channels_unfiltered

    print("\n" + "-" * 60)

    # Mode
    if args.mode == 'batch':
        print(f"  Mode:            BATCH (50% cost savings)")
    else:
        print(f"  Mode:            SYNC (per-video API calls)")

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
            print(f"  Channels:        All channels")

    # Model
    print(f"  Gemini model:    {config.GEMINI_MODEL}")

    # Batch-specific info
    if args.mode == 'batch':
        print(f"  Batch size:      {args.batch_size:,} max requests/job")
        phases = args.phase.upper()
        if phases == 'ALL':
            phases = 'PREPARE -> SUBMIT -> POLL -> IMPORT'
        print(f"\n  Phase: {phases}")

    print("-" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='YouTube Intelligence System - AI Analysis'
    )
    parser.add_argument(
        '--type', '-t',
        choices=['all', 'thumbnail', 'title_description'],
        default='all',
        help='Type of analysis to run (thumbnail=vision, title_description=combined text)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help='Limit videos per channel'
    )
    parser.add_argument(
        '--channel', '-c',
        type=str,
        default=None,
        help='Process only this channel ID'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Only validate configuration and connections'
    )

    # Batch mode arguments
    parser.add_argument(
        '--mode', '-m',
        choices=['sync', 'batch'],
        default='sync',
        help='Processing mode: sync (default, per-video) or batch (Gemini Batch API, 50%% cost savings)'
    )
    parser.add_argument(
        '--phase',
        choices=['all', 'prepare', 'submit', 'poll', 'import', 'status'],
        default='all',
        help='Batch phase to run (default: all phases sequentially)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=680,
        help='Maximum requests per batch job (default: 680 for Tier 1, use 50000 for Tier 2+)'
    )
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=None,
        help='Seconds between poll checks (default: from config/60s)'
    )
    parser.add_argument(
        '--job-name',
        type=str,
        default=None,
        help='Specific batch job name to poll/import'
    )
    parser.add_argument(
        '--loop',
        action='store_true',
        help='Loop batch jobs until all videos are analyzed (batch mode only)'
    )

    args = parser.parse_args()

    # Validate channel ID format if provided
    if args.channel:
        # YouTube channel IDs start with UC and are 24 characters long
        if not args.channel.startswith('UC') or len(args.channel) != 24:
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

    # For batch status, skip Gemini connection test (Config already loaded above)
    if args.mode == 'batch' and args.phase == 'status':
        _show_batch_status()
        return

    # Test Gemini connection (skip for batch import phase — it just reads files)
    if not (args.mode == 'batch' and args.phase == 'import'):
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

    if args.mode == 'batch':
        run_batch_mode(args)
    else:
        # Sync mode (existing behavior)
        if args.channel:
            # Process single channel
            if args.type == 'all':
                for analysis_type in ['thumbnail', 'title_description']:
                    print(f"\nProcessing {analysis_type} analysis for channel {args.channel}...")
                    processor = BatchProcessor(analysis_type)
                    stats = processor.process_channel(args.channel, limit=args.limit)
                    print(f"Completed: {stats['successful']} successful, {stats['failed']} failed")
            else:
                print(f"\nProcessing {args.type} analysis for channel {args.channel}...")
                processor = BatchProcessor(args.type)
                stats = processor.process_channel(args.channel, limit=args.limit)
                print(f"Completed: {stats['successful']} successful, {stats['failed']} failed")
        else:
            # Process all channels
            if args.type == 'all':
                run_all_analysis(limit_per_channel=args.limit)
            else:
                processor = BatchProcessor(args.type)
                processor.process_all_channels(limit=args.limit)

    print("\n" + "=" * 60)
    print("  Analysis Complete!")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()

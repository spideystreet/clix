"""Job search CLI commands."""

from __future__ import annotations

from typing import Annotated

import typer

from clix.cli.helpers import (
    get_client,
    is_compact_mode,
    is_json_mode,
    is_yaml_mode,
    output_compact,
    output_json,
    output_yaml,
    validate_output_flags,
)
from clix.display.formatter import format_job_detail, format_job_list, print_error

jobs_app = typer.Typer(no_args_is_help=True)


@jobs_app.command("search")
def jobs_search(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Search keyword (e.g. 'data engineer')")],
    location: Annotated[
        str, typer.Option("--location", "-l", help="Location filter (e.g. 'Paris')")
    ] = "",
    location_type: Annotated[
        list[str] | None,
        typer.Option("--location-type", help="Location type: remote, onsite, hybrid"),
    ] = None,
    employment_type: Annotated[
        list[str] | None,
        typer.Option(
            "--employment-type",
            "-e",
            help="Employment type: full_time, part_time, contract, internship",
        ),
    ] = None,
    seniority: Annotated[
        list[str] | None,
        typer.Option("--seniority", "-s", help="Seniority: entry_level, mid_level, senior"),
    ] = None,
    company: Annotated[str, typer.Option("--company", help="Filter by company name")] = "",
    industry: Annotated[str, typer.Option("--industry", help="Filter by industry")] = "",
    count: Annotated[int, typer.Option("--count", "-n", help="Number of results")] = 25,
    pages: Annotated[int, typer.Option("--pages", "-p", help="Number of pages")] = 1,
    compact: Annotated[
        bool, typer.Option("--compact", "-c", help="Compact JSON output for AI agents")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """Search for job listings on X/Twitter."""
    validate_output_flags(json_output, yaml_output)

    ctx.ensure_object(dict)
    if compact:
        ctx.obj["compact"] = True

    from clix.core.api import search_jobs

    all_jobs = []
    cursor = None

    with get_client(account) as client:
        for _ in range(pages):
            response = search_jobs(
                client,
                keyword=query,
                location=location,
                location_type=location_type,
                employment_type=employment_type,
                seniority_level=seniority,
                company=company,
                industry=industry,
                count=count,
                cursor=cursor,
            )
            all_jobs.extend(response.jobs)
            cursor = response.next_cursor
            if not response.has_more:
                break

    is_compact = is_compact_mode(ctx)
    if is_compact and json_output:
        raise typer.BadParameter("--compact and --json are mutually exclusive")

    if is_compact:
        output_compact(all_jobs, kind="jobs")
    elif is_json_mode(json_output):
        output_json([j.to_json_dict() for j in all_jobs])
    elif is_yaml_mode(yaml_output):
        output_yaml([j.to_json_dict() for j in all_jobs])
    else:
        format_job_list(all_jobs)


@jobs_app.command("view")
def jobs_view(
    job_id: Annotated[str, typer.Argument(help="Job listing ID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="YAML output")] = False,
    account: Annotated[str | None, typer.Option(help="Account name")] = None,
) -> None:
    """View details of a specific job listing."""
    validate_output_flags(json_output, yaml_output)

    from clix.core.api import get_job_detail

    with get_client(account) as client:
        job = get_job_detail(client, job_id)

    if not job:
        print_error(f"Job {job_id} not found")
        raise typer.Exit(1)

    if is_json_mode(json_output):
        output_json(job.to_json_dict())
    elif is_yaml_mode(yaml_output):
        output_yaml(job.to_json_dict())
    else:
        format_job_detail(job)

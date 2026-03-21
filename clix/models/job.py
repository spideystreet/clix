"""Pydantic models for X/Twitter job listings."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


class JobCompany(BaseModel):
    """Company that posted the job."""

    id: str
    name: str
    logo_url: str = ""

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> JobCompany:
        """Parse company from API response data."""
        return cls(
            id=data.get("rest_id", ""),
            name=data.get("core", {}).get("name", ""),
            logo_url=data.get("logo", {}).get("normal_url", ""),
        )


class Job(BaseModel):
    """A job listing on X/Twitter."""

    id: str
    title: str
    company: JobCompany
    location: str = ""
    location_type: str = ""
    redirect_url: str = ""
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str = ""
    formatted_salary: str = ""
    team: str = ""
    description: str = ""
    job_url: str = ""
    poster_handle: str = ""
    poster_name: str = ""
    poster_verified: bool = False
    poster_verified_type: str = ""

    def to_json_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return self.model_dump(mode="json")

    @classmethod
    def from_search_result(cls, item: dict[str, Any]) -> Job | None:
        """Parse a job from search result item."""
        try:
            rest_id = item.get("rest_id", "")
            result = item.get("result")
            if not result:
                return None

            core = result.get("core", {})
            company_data = result.get("company_profile_results", {}).get("result", {})
            company = JobCompany.from_api_data(company_data)

            user_data = result.get("user_results", {}).get("result", {})
            poster_handle = user_data.get("core", {}).get("screen_name", "")
            poster_name = user_data.get("core", {}).get("name", "")
            verification = user_data.get("verification", {})

            return cls(
                id=rest_id,
                title=core.get("title", ""),
                company=company,
                location=core.get("location", ""),
                redirect_url=core.get("redirect_url", ""),
                salary_min=core.get("salary_min"),
                salary_max=core.get("salary_max"),
                salary_currency=core.get("salary_currency_code", ""),
                formatted_salary=core.get("formatted_salary", ""),
                job_url=f"https://x.com/i/jobs/{rest_id}",
                poster_handle=poster_handle,
                poster_name=poster_name,
                poster_verified=verification.get("verified", False),
                poster_verified_type=verification.get("verified_type", ""),
            )
        except (KeyError, TypeError, IndexError):
            return None

    @classmethod
    def from_detail_result(cls, data: dict[str, Any]) -> Job | None:
        """Parse a job from detail response."""
        try:
            job_data = data.get("data", {}).get("jobData", {})
            rest_id = job_data.get("rest_id", "")
            result = job_data.get("result", {})

            core = result.get("core", {})
            company_data = result.get("company_profile_results", {}).get("result", {})
            company = JobCompany.from_api_data(company_data)

            description = ""
            raw_desc = core.get("job_description", "")
            if raw_desc:
                try:
                    desc_data = json.loads(raw_desc) if isinstance(raw_desc, str) else raw_desc
                    from clix.utils.article import article_to_markdown

                    description = article_to_markdown({"content_state": desc_data})
                except (json.JSONDecodeError, TypeError):
                    description = raw_desc

            return cls(
                id=rest_id,
                title=core.get("title", ""),
                company=company,
                location=core.get("location", ""),
                location_type=core.get("location_type", ""),
                redirect_url=core.get("external_url", ""),
                team=core.get("team", ""),
                description=description,
                job_url=core.get("job_page_url", f"https://x.com/i/jobs/{rest_id}"),
            )
        except (KeyError, TypeError, IndexError):
            return None


class JobSearchResponse(BaseModel):
    """Response from a job search query."""

    jobs: list[Job] = Field(default_factory=list)
    next_cursor: str | None = None

    @property
    def has_more(self) -> bool:
        """Whether there are more results to fetch."""
        return self.next_cursor is not None

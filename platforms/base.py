"""Abstract base for all platform scrapers/appliers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobListing:
    platform: str
    title: str
    company: str
    location: str
    job_url: str
    experience_required: str = ""
    job_description: str = ""
    ats_score: float = 0.0


class BasePlatform(ABC):
    name: str = "base"

    @abstractmethod
    def login(self) -> bool: ...

    @abstractmethod
    def search_jobs(self, role: str, location: str) -> list[JobListing]: ...

    @abstractmethod
    def apply_to_job(self, job: JobListing) -> bool: ...

    def close(self): ...

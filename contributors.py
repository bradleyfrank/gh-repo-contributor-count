#!/usr/bin/env python3

"""
Count unique contributors across GitHub repositories.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Type, Dict

import click
import logzero
from logzero import logger
from github import Github, GithubException

ORG_NAME = "bradleyfrank"
GH_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN")
DAYS_AGO = 90


def since_datetime(days: int) -> datetime:
    """Return a date (in datetime format) for a certain numbers of days in the past."""
    past_date = datetime.today() - timedelta(days=days)
    # TODO: Find a cleaner way to get ISO8601 as a Python datetime type.
    return datetime.fromisoformat(past_date.isoformat())


def find_recent_contributors(repository: Type[Github], since: datetime) -> Dict:
    """
    Iterates over all commits in a repository for the specified date range to find authors.
    """
    logger.info("analyzing commits for %s", repository.full_name)
    authors = {}

    commits = repository.get_commits(since=since)
    try:
        logger.debug("found %s total commits", commits.totalCount)
    except GithubException:
        logger.warning("skipping (empty repository)")
        return authors

    for commit in commits:
        author_name = commit.commit.author.name.lower()
        author_email = commit.commit.author.email
        logger.debug("found author %s [%s]", author_name, author_email)
        if (author_email, author_name) not in authors.items():
            authors[author_email] = author_name
        else:
            logger.warning("duplicate found: %s [%s]", author_name, author_email)
    return authors


@click.command()
@click.option("-o", "--org", type=str, default=ORG_NAME, help="organization name")
@click.option("-r", "--repos", type=str, help="repository names, comma separated")
@click.option("-d", "--debug", is_flag=True, default=False, help="show debugging")
def main(org: str, repos: str, debug: bool) -> Dict:
    """
    Counts unique contributors across repositories.

    \b
    Count repositories:
        ./metrics.py -r <repository1,repository2,...repositoryN>

    \b
    Specify an organization:
        ./contributors.py -o <org> -r <repos>
    """
    debug_level = logzero.DEBUG if debug else logzero.ERROR
    logzero.loglevel(debug_level)
    logzero.formatter(formatter=logzero.LogFormatter(fmt="%(color)s%(message)s%(end_color)s"))

    repo_stats = {"repositories": {}, "contributors": []}
    all_contributors = {}
    past_date = since_datetime(DAYS_AGO)
    github = Github(GH_TOKEN)

    if repos is None:
        logger.error("no repositories provided")
        sys.exit()

    for repo in repos.split(","):
        try:
            github_repository = github.get_repo(f"{org}/{repo}")
        except GithubException as error:
            logger.error("could not find repository: %s/%s", org, repo)
            logger.error(error)
            continue
        contributors = find_recent_contributors(github_repository, past_date)
        repo_stats["repositories"][repo] = len(contributors)
        all_contributors.update(contributors)

    if repo_stats["repositories"]:
        repo_stats["contributors"] = dict(sorted(all_contributors.items()))
        repo_stats["num_unique_contributors"] = len(repo_stats["contributors"])
        print(json.dumps(repo_stats, indent=4))


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()

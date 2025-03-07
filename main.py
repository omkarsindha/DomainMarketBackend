from fastapi import FastAPI, Query
from typing import List
import json
from test_xml_parser import NamecheapService

app = FastAPI()
domain_checker = NamecheapService()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/domains")
async def check_domains(domains: List[str] = Query(None)):
    """
    Check availability of domains.

    Args:
        domains: List of domains to check

    Returns:
        JSON response with domain availability information
    """
    if domains:
        result = domain_checker.check_domains(domains)
        return json.loads(result)


@app.get("/hardcoded_domains")
async def check_hard_domains():
    """
    If no domains are provided, it checks hardcoded test domains.\

    Returns:
        JSON response with hard coded domain availability information
    """
    result = domain_checker.check_hardcoded_domains()
    return json.loads(result)
import database as db
from fastmcp import FastMCP
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

db.init_db()

mcp = FastMCP("TimeTrack")

@mcp.tool
def log_time(employee_name : str, project : str, entry_date : str, hours : float, description : str):
    """ Log a time entry for an employee on a specific project. Date should be in YYYY-MM-DD format. """
    return db.log_time(employee_name, project, entry_date, hours, description)

@mcp.tool
def get_timesheet(employee_name : str, start_date : str, end_date : str):
    """ Retrieve the timesheet for an employee between two dates. Dates should be in YYYY-MM-DD format. """
    return db.get_timesheet(employee_name, start_date or None, end_date or None)

@mcp.tool
def get_project_summary(project : str):
    """ Retrieve a summary of time logged for a specific project. """
    return db.get_project_summary(project)

@mcp.tool
def list_projects():
    """ List all projects that have time logged. """
    return db.list_projects()

@mcp.resource("timesheet://projects")
def known_projects() -> list[str]:
    """ List all projects that have time logged. """
    return db.list_projects()

@mcp.prompt
def generate_weekly_report(employee_name: str, week_start: str) -> str:
    """Guides the AI to build a structured weekly hours report from this server's own tools."""
    return f"""Build a weekly report for {employee_name}, starting {week_start}.

1. Call get_timesheet with employee_name='{employee_name}', start_date='{week_start}'
2. Group the results by project
3. Present it as:
   {{employee_name}} -- Week of {week_start}
   [Project]: {{total hours for that project}}h
   Total: {{sum of all hours}}h

If no entries are found for that week, say so plainly instead of inventing data.
"""

mcp_app = mcp.http_app(path="/")


# ---------- Step 2: build the FastAPI app, lifespan wired in AT CONSTRUCTION ----------
app = FastAPI(title="TimeTrack", lifespan=mcp_app.lifespan)


class NewEntry(BaseModel):
    employee_name: str
    project: str
    entry_date: str
    hours: float
    description: str = ""


@app.get("/api/entries")
def api_list_entries():
    return db.list_all_entries()


@app.post("/api/entries")
def api_log_entry(entry: NewEntry):
    return db.log_time(entry.employee_name, entry.project, entry.entry_date, entry.hours, entry.description)


@app.get("/api/projects")
def api_list_projects():
    return db.list_projects()


@app.get("/api/projects/{project}/summary")
def api_project_summary(project: str):
    return db.get_project_summary(project)


@app.get("/api/timesheet/{employee_name}")
def api_get_timesheet(employee_name: str, start_date: str = None, end_date: str = None):
    return db.get_timesheet(employee_name, start_date, end_date)


@app.get("/")
def serve_index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/mcp", mcp_app)
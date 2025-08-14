from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED
from pathlib import Path
import subprocess, os, time

app = FastAPI()
security = HTTPBasic()

BASIC_USER = os.getenv("BASIC_USER","admin")
BASIC_PASS = os.getenv("BASIC_PASS","admin")

def auth(creds: HTTPBasicCredentials):
    if creds.username != BASIC_USER or creds.password != BASIC_PASS:
        return Response(status_code=HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate":"Basic"})
    return None

@app.get("/admin", response_class=HTMLResponse)
def index(credentials: HTTPBasicCredentials = security):
    a = auth(credentials)
    if a: return a
    return HTMLResponse('''<h1>FreeNETvpn Admin</h1>
    <ul>
      <li><a href="/admin/status">Docker status</a></li>
      <li><a href="/admin/backup">Create & download backup</a></li>
    </ul>''')

@app.get("/admin/status", response_class=HTMLResponse)
def status(credentials: HTTPBasicCredentials = security):
    a = auth(credentials); 
    if a: return a
    out = subprocess.check_output(["/usr/bin/docker","ps","--format","{{.Names}} -> {{.Status}}"]).decode()
    return HTMLResponse("<pre>"+out+"</pre>")

@app.get("/admin/backup")
def backup(credentials: HTTPBasicCredentials = security):
    a = auth(credentials); 
    if a: return a
    out_path = Path("/srv/backups")/f"freenetvpn-backup-{int(time.time())}.tar.gz"
    subprocess.check_call(["tar","czf",str(out_path),"/srv/services","/srv/host"])
    return FileResponse(str(out_path), filename=out_path.name)

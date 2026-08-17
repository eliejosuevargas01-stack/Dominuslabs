with open("project-hub/backend/app/api/endpoints/webhooks.py", "r") as f:
    content = f.read()

# Add import
if "run_in_threadpool" not in content:
    content = content.replace("from fastapi.responses import StreamingResponse", "from fastapi.concurrency import run_in_threadpool\nfrom fastapi.responses import StreamingResponse")

# We will replace all process_* calls
import re

content = re.sub(
    r"webhook_service\.process_deploy_webhook\(\s*db=db,\s*project_id=(.*?),\s*provider=(.*?),\s*status=(.*?),\s*deploy_url=(.*?),\s*deploy_date=(.*?)\s*\)",
    r"await run_in_threadpool(\n        webhook_service.process_deploy_webhook,\n        db, \1, \2, \3, \4, \5\n    )",
    content,
    flags=re.MULTILINE
)

content = re.sub(
    r"webhook_service\.process_github_webhook\(\s*db=db,\s*project_id=(.*?),\s*commit_hash=(.*?),\s*message=(.*?),\s*author=(.*?),\s*commit_date=(.*?)\s*\)",
    r"await run_in_threadpool(\n        webhook_service.process_github_webhook,\n        db, \1, \2, \3, \4, \5\n    )",
    content,
    flags=re.MULTILINE
)

with open("project-hub/backend/app/api/endpoints/webhooks.py", "w") as f:
    f.write(content)

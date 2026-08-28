import urllib.request
import json
import os

api_key = os.environ.get("API_KEY")
url = "https://jules.googleapis.com/v1alpha/sessions/13071902323146402623/activities?pageSize=100"
headers = {"X-Goog-Api-Key": api_key}

messages = []
while url:
    req = urllib.request.Request(url, headers=headers)
    resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    for act in resp.get("activities", []):
        if "chatMessage" in act:
            messages.append(act["chatMessage"])
        if "userFeedbackRequested" in act:
            messages.append(act["userFeedbackRequested"])
        if "userFeedbackProvided" in act:
            messages.append(act["userFeedbackProvided"])
        # print keys of one just in case
        for key in act.keys():
            if key.lower().find("message") != -1 or key.lower().find("feedback") != -1 or key.lower().find("question") != -1:
                messages.append(act)
    
    token = resp.get("nextPageToken")
    if token:
        url = f"https://jules.googleapis.com/v1alpha/sessions/13071902323146402623/activities?pageSize=100&pageToken={token}"
    else:
        url = None

print(json.dumps(messages, indent=2))

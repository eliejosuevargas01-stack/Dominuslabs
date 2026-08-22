with open('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/api/endpoints/webhooks.py', 'r') as f:
    content = f.read()

old_logic = """        elif isinstance(raw_body, dict):
            body_dict = raw_body
            if "messages" in raw_body and isinstance(raw_body["messages"], list):
                messages_list = raw_body["messages"]
            elif "mensagens" in raw_body and isinstance(raw_body["mensagens"], list):
                messages_list = raw_body["mensagens"]
            else:
                messages_list = [raw_body]"""

new_logic = """        elif isinstance(raw_body, dict):
            body_dict = raw_body
            if "messages" in raw_body and isinstance(raw_body["messages"], list):
                messages_list = raw_body["messages"]
            elif "mensagens" in raw_body and isinstance(raw_body["mensagens"], list):
                messages_list = raw_body["mensagens"]
            elif "data" in raw_body and isinstance(raw_body["data"], list) and raw_body.get("event") == "messages.update":
                # Flatten evolution API update events
                flattened = []
                for d in raw_body["data"]:
                    if isinstance(d, dict) and "update" in d and "key" in d:
                        flattened.append({
                            "id": d["key"].get("id"),
                            "status": d["update"].get("status"),
                            "_is_evolution_ack": True,
                            "key": d["key"]
                        })
                    else:
                        flattened.append(d)
                messages_list = flattened
            elif "data" in raw_body and isinstance(raw_body["data"], list) and raw_body.get("event") == "messages.upsert":
                messages_list = raw_body["data"]
            else:
                messages_list = [raw_body]"""

content = content.replace(old_logic, new_logic)

with open('/home/eliezer/Escritorio/dominuslabs/project-hub/backend/app/api/endpoints/webhooks.py', 'w') as f:
    f.write(content)

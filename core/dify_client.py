import requests


class DifyClient:
    def __init__(self, api_key, base_url: str = "https://api.dify.ai/v1"):
        self.api_key = api_key
        self.base_url = base_url

    def query(self, *args, **kwargs):
        # interface for subclasses to implement the api call entry point
        raise NotImplementedError("Subclasses must implement this method.")

    def _send_request(self, method, endpoint, json=None, params=None, stream=False):
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, json=json, params=params, headers=headers, stream=stream)
        return response

    def _send_request_with_files(self, method, endpoint, data, files):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, data=data, headers=headers, files=files)
        return response

    def message_feedback(self, message_id, rating, user):
        data = {"rating": rating, "user": user}
        return self._send_request("POST", f"/messages/{message_id}/feedbacks", data)

    def get_application_parameters(self, user):
        params = {"user": user}
        return self._send_request("GET", "/parameters", params=params)

    def file_upload(self, user, files):
        data = {"user": user}
        return self._send_request_with_files("POST", "/files/upload", data=data, files=files)


class ChatClient(DifyClient):

    def query(self, inputs, query, user, response_mode="blocking", files=None, conversation_id=None, auto_generate_name=False):
        return self.create_chat_messages(inputs, query, user, response_mode, conversation_id, files, auto_generate_name)

    def create_chat_messages(
        self, inputs, query, user, response_mode="blocking", conversation_id=None, files=None, auto_generate_name=False
    ):
        data = {
            "inputs": inputs,
            "query": query,
            "user": user,
            "response_mode": response_mode,
            "files": files,
            "auto_generate_name": auto_generate_name,
        }
        if conversation_id:
            data["conversation_id"] = conversation_id
        streaming = True if response_mode == "streaming" else False
        return self._send_request("POST", "/chat-messages", data, stream=streaming)

    def get_conversation_messages(self, user, conversation_id=None, first_id=None, limit=None):
        params = {"user": user}
        if conversation_id:
            params["conversation_id"] = conversation_id
        if first_id:
            params["first_id"] = first_id
        if limit:
            params["limit"] = limit
        return self._send_request("GET", "/messages", params=params)

    def get_conversations(self, user, last_id=None, limit=None, pinned=None):
        params = {"user": user, "last_id": last_id, "limit": limit, "pinned": pinned}
        return self._send_request("GET", "/conversations", params=params)

    def rename_conversation(self, conversation_id, name, user):
        data = {"name": name, "user": user}
        return self._send_request("POST", f"/conversations/{conversation_id}/name", data)


class CompletionClient(DifyClient):
    def query(self, inputs, query, user, response_mode="blocking", files=None, **kwargs):
        inputs["query"] = query
        return self.create_completion_messages(inputs, user, response_mode, files)

    def create_completion_messages(self, inputs, user, response_mode="blocking", files=None):
        data = {"inputs": inputs, "response_mode": response_mode, "user": user, "files": files}
        streaming = True if response_mode == "streaming" else False
        return self._send_request("POST", "/completion-messages", data, stream=streaming)


class WorkflowClient(DifyClient):
    def query(self, inputs, query, user, response_mode="blocking", files=None, **kwargs):
        inputs["query"] = query
        return self.workflow_run(inputs, user, response_mode, files)

    def workflow_run(self, inputs, user, response_mode="blocking", files=None):
        data = {"inputs": inputs, "response_mode": response_mode, "user": user, "files": files}
        streaming = True if response_mode == "streaming" else False
        return self._send_request("POST", "/workflows/run", data, stream=streaming)


if __name__ == "__main__":
    client = ChatClient(api_key="app-xxx", base_url="http://192.168.250.64/v1")
    # client = WorkflowClient(api_key="app-xxx", base_url="http://192.168.250.64/v1")
    # client = CompletionClient(api_key="app-xxx", base_url="http://192.168.250.64/v1")
    # 测试 streaming 模式
    query = "每月几号发工资？"
    user = "user"
    response_mode = "streaming"
    conversation_id = None
    files = None
    inputs = {}

    inputs["query"] = query
    response = client.query(inputs, query, user, response_mode, files, conversation_id=conversation_id)

    # 处理sse流式返回
    from sseclient import SSEClient
    import json

    if response.status_code != 200:
        print(response.text)
        exit(1)
    sse_client = SSEClient(response)
    for event in sse_client.events():
        # print(event.data)
        print(json.loads(event.data))

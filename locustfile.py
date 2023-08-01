from locust import HttpUser, task, between


class ChatUser(HttpUser):
    wait_time = between(60,61)

    def on_start(self):
        self.client.get("/")

    @task
    def ask_question(self):
        self.client.post("/chat", json={
            "history": [
                {
                "user": "What is included in my Northwind Health Plus plan that is not in standard?"
                }
            ],
            "approach": "rrr",
            "overrides": {
                "retrieval_mode": "hybrid",
                "semantic_ranker": True,
                "semantic_captions": False,
                "top": 3,
                "suggest_followup_questions": False
            }
            })

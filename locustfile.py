import random
import time

from locust import HttpUser, between, task


class ChatUser(HttpUser):
    wait_time = between(5, 20)

    @task
    def ask_question(self):
        self.client.get("/")
        time.sleep(5)
        self.client.post(
            "/chat",
            json={
                "history": [{"user": random.choice(["What is included in my Northwind Health Plus plan that is not in standard?", "What does a Product Manager do?", "What happens in a performance review?", "Whats your whistleblower policy?"])}],
                "approach": "rrr",
                "overrides": {"retrieval_mode": "hybrid", "semantic_ranker": True, "semantic_captions": False, "top": 3, "suggest_followup_questions": False},
            },
        )
        time.sleep(5)
        self.client.post(
            "/chat",
            json={
                "history": [
                    {
                        "user": "What happens in a performance review?",
                        "bot": "During the performance review at Contoso Electronics, the supervisor will discuss the employee's performance over the past year and provide feedback on areas for improvement. They will also provide an opportunity for the employee to discuss their goals and objectives for the upcoming year. The review is a two-way dialogue between managers and employees, and employees will receive a written summary of their performance review which will include a rating of their performance, feedback, and goals and objectives for the upcoming year [employee_handbook-3.pdf].",
                    },
                    {"user": "Does my plan cover eye exams?"},
                ],
                "approach": "rrr",
                "overrides": {"retrieval_mode": "hybrid", "semantic_ranker": True, "semantic_captions": False, "top": 3, "suggest_followup_questions": False},
            },
        )

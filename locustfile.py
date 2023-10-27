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
                "history": [
                    {
                        "content": random.choice(
                            [
                                "What are perceptions of the flu and its complications, and how has this changed?",
                                "What are the drivers and barriers that influence the decision to get vaccinated / recommend vaccination for the COVID and / or Flu? ",
                                "What is the best communication channel to deliver the messages to drive uptake of the flu vaccine?",
                                "What are the key messages that resonate the most to drive uptake of the flu vaccine?",
                            ]
                        ),
                        "role": "user",
                    },
                ],
                "overrides": {
                    "retrieval_mode": "hybrid",
                    "semantic_ranker": True,
                    "semantic_captions": False,
                    "top": 3,
                    "suggest_followup_questions": False,
                },
            },
        )
        time.sleep(5)
        self.client.post(
            "/chat",
            json={
                "history": [
                    {"content": "What is the best communication channel to deliver the messages to drive uptake of the flu vaccine?", "role": "user"},
                    {
                        "content": "For general public and patients, a generic e-mail to a group of patients may be effective, as it is currently used by 14% of healthcare professionals and there is an intention to improve this channel in the future. Additionally, providing engaging reminders to patients through pharmacists may also help drive vaccination rates. [23-0100-27.pdf].",
                        "role": "assistant",
                    },
                    {"content": "What are the key messages that resonate the most to drive uptake of the flu vaccine?", "role": "user"},
                ],
                "overrides": {
                    "retrieval_mode": "hybrid",
                    "semantic_ranker": True,
                    "semantic_captions": False,
                    "top": 3,
                    "suggest_followup_questions": False,
                },
            },
        )

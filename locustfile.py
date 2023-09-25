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
                        "user": random.choice(
                            [
                                "Why did the Commission propose a new NIS Directive?",
                                "How has the COVID-19 crisis influenced the new Directive?",
                                "Which sectors and types of entities will the NIS2 cover?",
                                "How will the NIS2 strengthen and streamline security requirements?",
                            ]
                        )
                    }
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
                    {
                        "user": "Which sectors and types of entities will the NIS2 cover?",
                        "bot": "The NIS2 covers entities from the following  sectors: Sectors of high criticality: energy (electricity, district heating and cooling, oil, gas and hydrogen); transport (air, rail, water and road); banking; financial market infrastructures; health including  manufacture of pharmaceutical products including vaccines; drinking water; waste water; digital infrastructure (internet exchange points; DNS service providers; TLD name registries; cloud computing service providers; data centre service providers; content delivery networks; trust service providers; providers of  public electronic communications networks and publicly available electronic communications services); ICT service management (managed service providers and managed security service providers), public administration and space. Other critical sectors: postal and courier services; waste management; chemicals; food; manufacturing of medical devices, computers and electronics, machinery and equipment, motor vehicles, trailers and semi-trailers and other transport equipment; digital providers (online market places, online search engines, and social networking service platforms) and research organisations.",
                    },
                    {"user": "Does my plan cover eye exams?"},
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

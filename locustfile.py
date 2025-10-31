import random
import time

from locust import HttpUser, between, task


class ChatUser(HttpUser):
    wait_time = between(5, 20)

    @task
    def ask_question(self):
        # Test home page
        with self.client.get("/", name="home", catch_response=True) as home_response:
            if home_response.status_code != 200:
                home_response.failure(f"Home page returned {home_response.status_code}: {home_response.text[:500]}")
                return
            home_response.success()

        time.sleep(self.wait_time())

        first_question = random.choice(
            [
                "What is included in my Northwind Health Plus plan that is not in standard?",
                "What does a Product Manager do?",
                "What happens in a performance review?",
                "Whats your whistleblower policy?",
            ]
        )

        # Send initial chat request
        with self.client.post(
            "/chat",
            name="initial chat",
            json={
                "messages": [
                    {
                        "content": first_question,
                        "role": "user",
                    },
                ],
                "context": {
                    "overrides": {
                        "retrieval_mode": "hybrid",
                        "semantic_ranker": True,
                        "semantic_captions": False,
                        "top": 3,
                        "suggest_followup_questions": True,
                    },
                },
            },
            catch_response=True,
        ) as response:
            # Check if the response is successful
            if response.status_code != 200:
                response.failure(f"Chat request failed with {response.status_code}: {response.text[:500]}")
                return

            # Try to parse JSON
            try:
                response_data = response.json()
            except Exception as e:
                response.failure(f"Failed to parse JSON: {str(e)}, Response: {response.text[:500]}")
                return

            # Check if response has the expected structure
            if "context" not in response_data or "followup_questions" not in response_data.get("context", {}):
                response.failure(f"Response missing expected fields: {response.text[:500]}")
                return

            if not response_data["context"]["followup_questions"]:
                # No follow-up questions, just mark as success and return
                response.success()
                return

            response.success()
            # Use one of the follow up questions
            follow_up_question = random.choice(response_data["context"]["followup_questions"])
            result_message = response_data["message"]["content"]

        time.sleep(self.wait_time())

        # Send follow-up chat request
        with self.client.post(
            "/chat",
            name="follow up chat",
            json={
                "messages": [
                    {"content": first_question, "role": "user"},
                    {
                        "content": result_message,
                        "role": "assistant",
                    },
                    {"content": follow_up_question, "role": "user"},
                ],
                "context": {
                    "overrides": {
                        "retrieval_mode": "hybrid",
                        "semantic_ranker": True,
                        "semantic_captions": False,
                        "top": 3,
                        "suggest_followup_questions": False,
                    },
                },
            },
            catch_response=True,
        ) as followup_response:
            if followup_response.status_code == 200:
                followup_response.success()
            else:
                followup_response.failure(f"Follow-up failed with {followup_response.status_code}: {followup_response.text[:500]}")

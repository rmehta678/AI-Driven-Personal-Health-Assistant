from locust import HttpUser, task, between

class WHOOPUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def connect(self):
        self.client.get("/whoop/connect")

    @task
    def ingest(self):
        self.client.get("/whoop/ingest")

# Run: locust -f locustfile.py --host=http://localhost:5000
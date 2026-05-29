"""Backend tests for Agora Conversational AI + Aria text chat backend."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://agora-avatar-chat.preview.emergentagent.com').rstrip('/')


@pytest.fixture
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ───────────────── Aria text chat (Emergent LLM) ─────────────────
class TestChatText:
    def test_chat_text_success(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/chat-text", json={
            "message": "Tell me about engine",
            "car_id": "amg-gt",
            "car_name": "Mercedes-AMG GT R",
            "car_tagline": "577 HP V8",
        }, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "text" in data and isinstance(data["text"], str) and len(data["text"]) > 0
        assert "session_id" in data and isinstance(data["session_id"], str) and len(data["session_id"]) > 0

    def test_chat_text_empty_returns_400(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/chat-text", json={
            "message": "",
            "car_id": "amg-gt",
            "car_name": "Mercedes-AMG GT R",
            "car_tagline": "577 HP V8",
        }, timeout=30)
        assert r.status_code == 400, r.text

    def test_chat_text_session_persists(self, api_client):
        r1 = api_client.post(f"{BASE_URL}/api/chat-text", json={
            "message": "Hello",
            "car_id": "amg-gt",
            "car_name": "Mercedes-AMG GT R",
            "car_tagline": "577 HP V8",
        }, timeout=60)
        assert r1.status_code == 200
        sid = r1.json()["session_id"]
        r2 = api_client.post(f"{BASE_URL}/api/chat-text", json={
            "message": "Tell me more",
            "car_id": "amg-gt",
            "car_name": "Mercedes-AMG GT R",
            "car_tagline": "577 HP V8",
            "session_id": sid,
        }, timeout=60)
        assert r2.status_code == 200
        assert r2.json()["session_id"] == sid


# ───────────────── Agora Conversational AI ─────────────────
class TestAgora:
    agent_id_holder = {}

    def test_agora_start(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/agora/start", json={
            "car_id": "amg-gt",
            "car_name": "Mercedes-AMG GT R",
            "car_tagline": "577 HP V8",
        }, timeout=45)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("app_id", "channel", "rtc_token", "uid", "agent_id", "agent_uid"):
            assert key in data, f"missing {key} in response: {data}"
        assert isinstance(data["app_id"], str) and len(data["app_id"]) > 0
        assert isinstance(data["channel"], str) and data["channel"].startswith("aria-")
        assert isinstance(data["rtc_token"], str) and len(data["rtc_token"]) > 10
        assert isinstance(data["uid"], int) and data["uid"] > 0
        assert isinstance(data["agent_id"], str) and len(data["agent_id"]) > 0
        assert isinstance(data["agent_uid"], int) and data["agent_uid"] > 0
        TestAgora.agent_id_holder["agent_id"] = data["agent_id"]

    def test_agora_stop(self, api_client):
        agent_id = TestAgora.agent_id_holder.get("agent_id")
        if not agent_id:
            # Get a fresh one
            r0 = api_client.post(f"{BASE_URL}/api/agora/start", json={
                "car_id": "amg-gt",
                "car_name": "Mercedes-AMG GT R",
                "car_tagline": "577 HP V8",
            }, timeout=45)
            assert r0.status_code == 200, r0.text
            agent_id = r0.json()["agent_id"]
        r = api_client.post(f"{BASE_URL}/api/agora/stop", json={"agent_id": agent_id}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Endpoint returns {"ok": true} on success, or {"ok": false, status, detail} on Agora error
        assert "ok" in data

    def test_agora_stop_missing_agent_id(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/agora/stop", json={"agent_id": ""}, timeout=15)
        assert r.status_code == 400, r.text


# ───────────────── Existing endpoints regression ─────────────────
class TestExistingEndpoints:
    def test_status_post_and_get(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/status", json={"client_name": "TEST_agora_iter2"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["client_name"] == "TEST_agora_iter2"
        assert "id" in data
        g = api_client.get(f"{BASE_URL}/api/status", timeout=15)
        assert g.status_code == 200
        items = g.json()
        assert any(s["client_name"] == "TEST_agora_iter2" for s in items)

    def test_leads_post_and_get(self, api_client):
        payload = {
            "name": "TEST_Iter2_User",
            "phone": "+10000000000",
            "location": "Test City",
            "car_id": "amg-gt",
            "car_name": "Mercedes-AMG GT R",
        }
        r = api_client.post(f"{BASE_URL}/api/leads", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == "TEST_Iter2_User"
        assert "id" in data
        g = api_client.get(f"{BASE_URL}/api/leads", timeout=15)
        assert g.status_code == 200
        assert any(l["name"] == "TEST_Iter2_User" for l in g.json())

    def test_leads_validation(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/leads", json={
            "name": "", "phone": "", "location": "",
            "car_id": "x", "car_name": "y",
        }, timeout=15)
        assert r.status_code == 400


# ───────────────── Old D-ID endpoint must be gone ─────────────────
class TestOldEndpointsRemoved:
    def test_chat_with_avatar_is_gone(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/chat-with-avatar", json={"message": "hi"}, timeout=15)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

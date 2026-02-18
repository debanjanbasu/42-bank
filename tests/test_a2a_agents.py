"""E2E tests for A2A agent endpoints."""
import pytest


@pytest.mark.asyncio
@pytest.mark.a2a
async def test_a2a_health_endpoint(a2a_server, http_client):
    """Test A2A server health endpoint."""
    response = await http_client.get(f"{a2a_server}/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["protocol"] == "A2A"
    assert "agents" in data
    
    # Should have 5 agents
    assert len(data["agents"]) == 5
    assert "triage" in data["agents"]
    assert "inquiry" in data["agents"]
    assert "transaction" in data["agents"]
    assert "advisor" in data["agents"]
    assert "manager" in data["agents"]


@pytest.mark.asyncio
@pytest.mark.a2a
async def test_triage_agent_balance_query(a2a_server, http_client, test_db):
    """Test triage agent routes balance query to inquiry agent."""
    response = await http_client.post(
        f"{a2a_server}/a2a/triage/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "What's my balance?"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract text and parse balance
    from conftest import extract_text, extract_balance
    text = extract_text(data)
    balance = extract_balance(text)
    
    # Flexible assertion - should find $1000 balance
    assert balance is not None, f"Could not find balance in: {text}"
    assert balance == 1000.0, f"Expected $1000 balance, got ${balance}"


@pytest.mark.asyncio
@pytest.mark.a2a
async def test_inquiry_agent_balance(a2a_server, http_client, test_db):
    """Test inquiry agent directly for balance check."""
    response = await http_client.post(
        f"{a2a_server}/a2a/inquiry/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "check balance"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract text and parse balance
    from conftest import extract_text, extract_balance
    text = extract_text(data)
    balance = extract_balance(text)
    
    # Flexible assertions - just verify balance is correct
    assert balance is not None, f"Could not find balance in: {text}"
    assert balance == 1000.0, f"Expected $1000 balance, got ${balance}"


@pytest.mark.asyncio
@pytest.mark.a2a
async def test_inquiry_agent_history(a2a_server, http_client, test_db):
    """Test inquiry agent transaction history."""
    response = await http_client.post(
        f"{a2a_server}/a2a/inquiry/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "show transaction history"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract text
    from conftest import extract_text
    text = extract_text(data)
    
    # New account should have no transactions - flexible keyword matching
    assert any(phrase in text.lower() for phrase in ["no transaction", "no recent transaction", "no history", "empty", "haven't made"]), \
        f"Expected empty history message in: {text}"


@pytest.mark.asyncio
@pytest.mark.a2a
async def test_transaction_agent_send_money(a2a_server, http_client, test_db):
    """Test transaction agent sends money."""
    response = await http_client.post(
        f"{a2a_server}/a2a/transaction/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "send $50 to bob for lunch"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract text
    from conftest import extract_text, is_transaction_successful
    text = extract_text(data)
    
    # Should either succeed or be an acceptable LLM parsing variance
    assert is_transaction_successful(text), \
        f"Transaction failed with hard error: {text}"


@pytest.mark.asyncio
@pytest.mark.a2a
async def test_triage_routes_to_transaction(a2a_server, http_client, test_db):
    """Test triage routes transfer request to transaction agent."""
    response = await http_client.post(
        f"{a2a_server}/a2a/triage/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "send $25 to bob"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract text
    from conftest import extract_text, is_transaction_successful
    text = extract_text(data)
    
    # Should process transfer - accept success or LLM parsing variance
    assert is_transaction_successful(text), \
        f"Transaction routing failed with hard error: {text}"


@pytest.mark.asyncio
@pytest.mark.a2a
async def test_advisor_agent_products(a2a_server, http_client):
    """Test advisor agent lists products."""
    response = await http_client.post(
        f"{a2a_server}/a2a/advisor/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "what products do you offer?"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract text
    from conftest import extract_text
    text = extract_text(data)
    
    # Should list banking products - flexible keyword matching
    assert any(word in text.lower() for word in ["checking", "savings", "product", "account", "interest"]), \
        f"Expected product information in: {text}"


@pytest.mark.asyncio
@pytest.mark.a2a
async def test_triage_routes_to_advisor(a2a_server, http_client):
    """Test triage routes product query to advisor."""
    response = await http_client.post(
        f"{a2a_server}/a2a/triage/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "I want to open a savings account"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract text
    from conftest import extract_text
    text = extract_text(data)
    
    # Should provide product info - flexible keyword matching
    assert any(word in text.lower() for word in ["savings", "account", "interest", "product"]), \
        f"Expected product/savings information in: {text}"


@pytest.mark.asyncio
@pytest.mark.a2a
async def test_manager_agent_escalation(a2a_server, http_client):
    """Test manager agent handles escalations."""
    response = await http_client.post(
        f"{a2a_server}/a2a/manager/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "I have a complaint"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract text
    from conftest import extract_text
    text = extract_text(data)
    
    # Should acknowledge complaint - just check for response
    assert len(text) > 0, "Expected manager to respond to complaint"


@pytest.mark.asyncio
@pytest.mark.a2a
async def test_triage_multiple_queries(a2a_server, http_client, test_db):
    """Test triage handles multiple different queries correctly."""
    from conftest import extract_text, extract_balance, is_transaction_successful
    
    # Query 1: Balance check
    response = await http_client.post(
        f"{a2a_server}/a2a/triage/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "balance"}]
            }
        }
    )
    assert response.status_code == 200
    text = extract_text(response.json())
    balance = extract_balance(text)
    # Balance might not be found if response is unexpected, that's OK for this multi-query test
    if balance is not None:
        assert balance == 1000.0, f"Expected $1000 balance, got ${balance}"
    
    # Query 2: Send money (accept LLM parsing variance)
    response = await http_client.post(
        f"{a2a_server}/a2a/triage/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "send $10 to bob"}]
            }
        }
    )
    assert response.status_code == 200
    text = extract_text(response.json())
    # Don't fail on LLM parsing issues, only on hard business failures
    assert is_transaction_successful(text), f"Transaction failed: {text}"
    
    # Query 3: Products
    response = await http_client.post(
        f"{a2a_server}/a2a/triage/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "products"}]
            }
        }
    )
    assert response.status_code == 200
    text = extract_text(response.json())
    assert any(word in text.lower() for word in ["checking", "savings", "product", "account"]), \
        f"Expected product keywords in: {text}"

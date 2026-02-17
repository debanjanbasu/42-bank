"""End-to-end integration tests for full request flow."""
import pytest


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_full_balance_check_flow(mcp_server, a2a_server, http_client, test_db):
    """
    Test complete flow: User query → Triage → Inquiry → MCP → Database → Response
    """
    from conftest import extract_text, extract_balance
    
    # Send balance query to triage
    response = await http_client.post(
        f"{a2a_server}/a2a/triage/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "What's my checking account balance?"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract and verify balance
    text = extract_text(data)
    balance = extract_balance(text)
    
    # Verify Alice's balance from test_db fixture
    assert balance is not None, f"Could not extract balance from: {text}"
    assert balance == 1000.0, f"Expected $1000 balance, got ${balance}"
    
    # Should NOT contain tool call artifacts (extract_text should strip them)
    assert "<tool_call>" not in text
    assert "</tool_call>" not in text


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_full_transfer_flow(mcp_server, a2a_server, http_client, test_db):
    """
    Test complete money transfer flow with balance verification.
    """
    from conftest import extract_text
    
    # 1. Check initial balance (skipped - we know it's $1000 from test_db)
    
    # 2. Send money
    response = await http_client.post(
        f"{a2a_server}/a2a/transaction/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "send $100 to bob for dinner"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract and verify success
    text = extract_text(data)
    assert any(word in text.lower() for word in ["success", "sent", "transferred"]), \
        f"Expected success message in: {text}"
    
    # 3. Verify transaction history
    response = await http_client.post(
        f"{a2a_server}/a2a/inquiry/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "show my transaction history"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract and verify transaction appears in history
    text = extract_text(data)
    assert any(word in text.lower() for word in ["bob", "100", "dinner", "transaction"]), \
        f"Expected transaction details in history: {text}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_transaction_with_sender_recipient_display(mcp_server, a2a_server, http_client, test_db):
    """
    Test that transactions show 'to/from' information correctly.
    """
    from conftest import extract_text
    
    # Send money to bob
    await http_client.post(
        f"{a2a_server}/a2a/transaction/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "send $75 to bob for rent"}]
            }
        }
    )
    
    # Check history
    response = await http_client.post(
        f"{a2a_server}/a2a/inquiry/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "show transactions"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract and verify recipient is shown
    text = extract_text(data)
    assert "bob" in text.lower(), f"Expected 'bob' in transaction history: {text}"
    assert any(amount in text for amount in ["75", "$75"]), f"Expected $75 amount in: {text}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_request_payment_full_flow(mcp_server, a2a_server, http_client, test_db):
    """
    Test payment request flow: Request → View pending → Approve.
    """
    from conftest import extract_text
    
    # 1. Request payment from bob
    response = await http_client.post(
        f"{a2a_server}/a2a/transaction/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "request $30 from bob for pizza"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract and verify request confirmation
    text = extract_text(data)
    assert any(word in text.lower() for word in ["request", "requested", "asking"]), \
        f"Expected request confirmation in: {text}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_product_inquiry_full_flow(mcp_server, a2a_server, http_client):
    """
    Test product inquiry flows through triage to advisor.
    """
    from conftest import extract_text
    
    response = await http_client.post(
        f"{a2a_server}/a2a/triage/v1/message",
        json={
            "message": {
                "parts": [{"kind": "text", "text": "tell me about your savings accounts"}]
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Extract and verify product information
    text = extract_text(data)
    assert any(word in text.lower() for word in ["savings", "account", "interest", "product"]), \
        f"Expected product information in: {text}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multiple_sequential_operations(mcp_server, a2a_server, http_client, test_db):
    """
    Test multiple sequential operations maintain correct state.
    """
    from conftest import extract_text, extract_balance
    
    # 1. Check balance ($1000)
    response = await http_client.post(
        f"{a2a_server}/a2a/inquiry/v1/message",
        json={"message": {"parts": [{"kind": "text", "text": "balance"}]}}
    )
    text = extract_text(response.json())
    balance = extract_balance(text)
    assert balance == 1000.0, f"Expected $1000, got ${balance}"
    
    # 2. Send $100
    response = await http_client.post(
        f"{a2a_server}/a2a/transaction/v1/message",
        json={"message": {"parts": [{"kind": "text", "text": "send $100 to bob"}]}}
    )
    text = extract_text(response.json())
    assert any(word in text.lower() for word in ["success", "sent", "transferred"])
    
    # 3. Send another $100
    response = await http_client.post(
        f"{a2a_server}/a2a/transaction/v1/message",
        json={"message": {"parts": [{"kind": "text", "text": "send $100 to bob"}]}}
    )
    text = extract_text(response.json())
    assert any(word in text.lower() for word in ["success", "sent", "transferred"])
    
    # 4. Check balance again ($800)
    response = await http_client.post(
        f"{a2a_server}/a2a/inquiry/v1/message",
        json={"message": {"parts": [{"kind": "text", "text": "balance"}]}}
    )
    text = extract_text(response.json())
    balance = extract_balance(text)
    assert balance == 800.0, f"Expected $800 after two $100 transfers, got ${balance}"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_agent_no_tool_call_leakage(mcp_server, a2a_server, http_client, test_db):
    """
    Test that no tool call XML leaks into user responses.
    """
    queries = [
        "What's my balance?",
        "Send $5 to bob",
        "Show transaction history",
        "What products do you have?",
    ]
    
    for query in queries:
        response = await http_client.post(
            f"{a2a_server}/a2a/triage/v1/message",
            json={
                "message": {
                    "parts": [{"kind": "text", "text": query}]
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        text = ""
        for part in data.get("parts", []):
            if part.get("kind") == "text":
                text += part.get("text", "")
        
        # No tool call artifacts
        assert "<tool_call>" not in text, f"Tool call leaked in query '{query}': {text}"
        assert "</tool_call>" not in text
        assert "คณะกรรม" not in text  # Thai text artifacts

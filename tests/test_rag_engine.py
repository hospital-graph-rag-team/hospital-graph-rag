import pytest
import json
from unittest.mock import MagicMock
from rag.engine import (
    run_clinical_query,
    run_clinical_query_detailed,
    execute_tool_call,
    _validate_tool_arguments,
    _check_safety_refusals,
    _extract_citations,
    TOOLS,
    MODEL_NAME,
)


# Helper to build a mock ChatCompletion response
def make_assistant_message(content=None, tool_calls=None):
    msg = MagicMock()
    msg.role = "assistant"
    msg.content = content
    msg.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def make_tool_call(call_id, func_name, args_dict):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = func_name
    tc.function.arguments = json.dumps(args_dict) if isinstance(args_dict, dict) else args_dict
    return tc


# =====================================================================
# 1. Tool Registration & Schemas
# =====================================================================

def test_tool_registration_and_schemas():
    """Verify that all 8 expected tools are registered with valid function schemas."""
    registered_names = {t["function"]["name"] for t in TOOLS}
    expected_tools = {
        "get_patient_directory",
        "get_patient_profile",
        "get_patient_timeline",
        "get_lab_trends",
        "get_followup_comparison",
        "get_medication_outcomes",
        "get_patient_history",
        "get_best_medications_for_condition",
    }
    assert expected_tools.issubset(registered_names)
    for tool in TOOLS:
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]


# =====================================================================
# 2. Public Interface Compatibility
# =====================================================================

def test_public_interface_compatibility():
    """Verify that run_clinical_query returns a string matching legacy expectations."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_assistant_message(
        content="Patient P101 has 3 recorded hospital visits."
    )

    answer = run_clinical_query("Tell me about P101", client=mock_client)
    assert isinstance(answer, str)
    assert "P101" in answer


# =====================================================================
# 3. Safety Refusals
# =====================================================================

def test_safety_refusal_delete_mutation():
    """Requests to delete or modify records must trigger immediate refusal without calling the API."""
    mock_client = MagicMock()
    res = run_clinical_query_detailed("Delete patient P101 from the database", client=mock_client)

    assert res["status"] == "refusal"
    assert "cannot modify or delete" in res["answer"].lower()
    mock_client.chat.completions.create.assert_not_called()


def test_safety_refusal_personal_medical_advice():
    """Requests for personal medical diagnosis or prescription advice must trigger immediate refusal."""
    mock_client = MagicMock()
    res = run_clinical_query_detailed("Which medication should I personally take for diabetes?", client=mock_client)

    assert res["status"] == "refusal"
    assert "cannot provide personalized medical" in res["answer"].lower()
    mock_client.chat.completions.create.assert_not_called()


def test_empty_query_handling():
    """Empty or whitespace user query must return error status."""
    res = run_clinical_query_detailed("   ")
    assert res["status"] == "error"
    assert "empty query" in res["error"].lower()


# =====================================================================
# 4. Tool Execution & Validation
# =====================================================================

def test_validate_tool_arguments_unexpected():
    """Unexpected arguments must be rejected."""
    err = _validate_tool_arguments("get_patient_profile", {"patient_id": "P101", "drop_table": True})
    assert err is not None
    assert "unexpected argument" in err.lower()


def test_validate_tool_arguments_missing_required():
    """Missing or empty required arguments must be rejected."""
    err = _validate_tool_arguments("get_patient_profile", {"patient_id": ""})
    assert err is not None
    assert "requires non-empty" in err.lower()


def test_unknown_tool_name():
    """Unknown tool call must return an error response."""
    data, summary = execute_tool_call("unknown_tool", {})
    assert "error" in data
    assert "unknown tool" in data["error"].lower()


def test_valid_single_tool_execution(monkeypatch):
    """Verify single-tool execution round followed by final synthesis."""
    mock_client = MagicMock()

    tc = make_tool_call("call_01", "get_patient_profile", {"patient_id": "P101"})
    # Round 1 returns tool call; Round 2 returns final text
    mock_client.chat.completions.create.side_effect = [
        make_assistant_message(content=None, tool_calls=[tc]),
        make_assistant_message(content="James Jones (P101) has 3 hospital visits recorded."),
    ]

    # Mock the underlying retrieval call
    monkeypatch.setattr(
        "rag.engine.get_patient_profile",
        lambda pid: {"patient_id": "P101", "name": "James Jones", "visit_count": 3}
    )

    res = run_clinical_query_detailed("Profile of P101", client=mock_client)
    assert res["status"] == "success"
    assert len(res["tool_calls"]) == 1
    assert res["tool_calls"][0]["tool"] == "get_patient_profile"
    assert "P101" in res["citations"]


def test_multiple_tool_calls_single_turn(monkeypatch):
    """Model emits multiple tool calls in a single turn."""
    mock_client = MagicMock()

    tc1 = make_tool_call("call_01", "get_patient_profile", {"patient_id": "P101"})
    tc2 = make_tool_call("call_02", "get_lab_trends", {"patient_id": "P101", "test_name": "LDL Cholesterol"})

    mock_client.chat.completions.create.side_effect = [
        make_assistant_message(content=None, tool_calls=[tc1, tc2]),
        make_assistant_message(content="Patient P101 profile and lab trends retrieved."),
    ]

    monkeypatch.setattr("rag.engine.get_patient_profile", lambda pid: {"patient_id": pid})
    monkeypatch.setattr("rag.engine.get_lab_trends", lambda pid, test_name=None: [{"biomarker": "LDL"}])

    res = run_clinical_query_detailed("P101 details and labs", client=mock_client)
    assert res["status"] == "success"
    assert len(res["tool_calls"]) == 2


def test_malformed_json_arguments():
    """Malformed JSON in tool arguments must be trapped gracefully without crashing the loop."""
    mock_client = MagicMock()

    tc = MagicMock()
    tc.id = "bad_call"
    tc.function.name = "get_patient_profile"
    tc.function.arguments = "{\"patient_id\": \"P101\" broken json"

    mock_client.chat.completions.create.side_effect = [
        make_assistant_message(content=None, tool_calls=[tc]),
        make_assistant_message(content="Unable to complete because arguments were invalid."),
    ]

    res = run_clinical_query_detailed("Profile of P101", client=mock_client)
    assert res["status"] == "success"
    assert any("failed parsing arguments" in tc_info["summary"].lower() for tc_info in res["tool_calls"])


def test_repeated_identical_tool_call_protection(monkeypatch):
    """Identical tool calls with identical arguments in the same session are skipped from re-execution."""
    mock_client = MagicMock()

    tc1 = make_tool_call("c1", "get_patient_profile", {"patient_id": "P101"})
    tc2 = make_tool_call("c2", "get_patient_profile", {"patient_id": "P101"})  # Duplicate

    mock_client.chat.completions.create.side_effect = [
        make_assistant_message(content=None, tool_calls=[tc1]),
        make_assistant_message(content=None, tool_calls=[tc2]),
        make_assistant_message(content="Final summary after duplicate suppressed."),
    ]

    call_count = {"count": 0}
    def mock_profile(pid):
        call_count["count"] += 1
        return {"patient_id": pid}

    monkeypatch.setattr("rag.engine.get_patient_profile", mock_profile)

    res = run_clinical_query_detailed("Test query", client=mock_client)
    assert res["status"] == "success"
    # Underlying function should only be called once; second call is intercepted
    assert call_count["count"] == 1
    assert any("skipped identical" in tc_info["summary"].lower() for tc_info in res["tool_calls"])


# =====================================================================
# 5. Loop Limits & Error Handling
# =====================================================================

def test_max_rounds_enforcement(monkeypatch):
    """The agent must terminate when reaching max_rounds and return limit_reached status."""
    mock_client = MagicMock()

    # Always return another tool call
    mock_client.chat.completions.create.side_effect = [
        make_assistant_message(content=None, tool_calls=[make_tool_call(f"c_{i}", "get_patient_directory", {})])
        for i in range(10)
    ]
    monkeypatch.setattr("rag.engine.get_patient_directory", lambda: [])

    res = run_clinical_query_detailed("Infinite loop test", client=mock_client, max_rounds=3)
    assert res["status"] == "limit_reached"
    assert "maximum allowed interaction rounds" in res["answer"].lower()


def test_max_tool_calls_enforcement(monkeypatch):
    """Reject tool calls that exceed max_tool_calls limit."""
    mock_client = MagicMock()

    # Emit 4 tool calls in one turn when limit is 2
    tool_calls = [
        make_tool_call(f"c_{i}", "get_patient_profile", {"patient_id": f"P10{i}"})
        for i in range(4)
    ]
    mock_client.chat.completions.create.side_effect = [
        make_assistant_message(content=None, tool_calls=tool_calls),
        make_assistant_message(content="Partial synthesis."),
    ]
    monkeypatch.setattr("rag.engine.get_patient_profile", lambda pid: {"patient_id": pid})

    res = run_clinical_query_detailed("Test max calls", client=mock_client, max_tool_calls=2)
    assert res["status"] == "success"
    # 2 succeeded, 2 were rejected due to limit
    limit_notices = [tc for tc in res["tool_calls"] if "exceeded maximum" in tc["summary"].lower()]
    assert len(limit_notices) == 2


def test_api_timeout_error_handling():
    """Client API errors must be handled gracefully without unhandled exceptions."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API connection timed out after 30s")

    res = run_clinical_query_detailed("Test timeout", client=mock_client)
    assert res["status"] == "error"
    assert "API error" in res["answer"]


# =====================================================================
# 6. Structured Output & Context
# =====================================================================

def test_structured_response_json_compatibility():
    """Detailed response must serialize cleanly to JSON."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_assistant_message(content="Answer text.")

    res = run_clinical_query_detailed("Test query", client=mock_client)
    serialized = json.dumps(res)
    assert isinstance(serialized, str)


def test_patient_context_injection():
    """Selected patient ID is injected into prompt context."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_assistant_message(content="Answer text.")

    run_clinical_query_detailed("How are the lab values?", selected_patient_id="P101", client=mock_client)
    call_args = mock_client.chat.completions.create.call_args[1]
    messages = call_args["messages"]
    user_msgs = [m for m in messages if isinstance(m, dict) and m.get("role") == "user"]
    assert len(user_msgs) > 0
    assert "Selected Patient ID is P101" in user_msgs[0]["content"]


def test_citation_extraction():
    """Citations matching hospital entity IDs are extracted and deduplicated."""
    text = "Patient P101 visited on V301, diagnosed with D0001 and prescribed RX0001. Lab test T0001 showed changes. Repeat P101."
    cites = _extract_citations(text)
    assert cites == ["P101", "V301", "D0001", "RX0001", "T0001"]

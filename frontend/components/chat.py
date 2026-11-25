import streamlit as st
from typing import Optional, Dict, Any, List

from src.rag.engine import run_clinical_query_detailed


def render_ai_assistant(selected_patient_id: Optional[str]):
    """
    Renders the conversational AI Assistant powered by the Groq ReAct Clinical RAG engine.
    Integrates run_clinical_query_detailed with context injection, citation validation,
    and transparent evidence inspection.
    """
    st.subheader("Clinical AI Assistant")
    st.caption("Ask natural-language clinical questions powered by Groq (`openai/gpt-oss-120b`) and Neo4j Graph Retrieval.")

    # 1. Active Context Header
    if selected_patient_id:
        st.info(f"🎯 **Active Patient Context:** `{selected_patient_id}` (Queries will prioritize this patient's clinical records)")
    else:
        st.info("🌐 **Active Context:** General Cohort (No specific patient selected. Cohort-level queries will be prioritized)")

    # 2. Session State Initialization for Chat
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "chat_patient_id" not in st.session_state:
        st.session_state["chat_patient_id"] = selected_patient_id

    # Detect patient switch and isolate/reset chat history to prevent cross-patient context contamination
    if st.session_state["chat_patient_id"] != selected_patient_id:
        st.session_state["messages"] = []
        st.session_state["chat_patient_id"] = selected_patient_id
        st.toast(f"Switched context to {selected_patient_id or 'General Cohort'}. Conversation reset.", icon="🔄")

    # Top Controls: Suggested Questions & Clear Chat
    ctrl_col1, ctrl_col2 = st.columns([4, 1])
    with ctrl_col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state["messages"] = []
            st.rerun()

    # Suggested Prompts
    st.markdown("**Suggested Questions:**")
    if selected_patient_id:
        suggestions = [
            f"Show complete medical history for patient {selected_patient_id}.",
            f"How have patient {selected_patient_id}'s lab test values changed?",
            f"Compare patient {selected_patient_id}'s consecutive hospital visits."
        ]
    else:
        suggestions = [
            "Compare synthetic medication outcomes for Type 2 Diabetes.",
            "How many unique patients and visit transitions were analysed for Hypertension?",
            "Which medication should I personally take for diabetes?"
        ]

    cols = st.columns(len(suggestions))
    prompt_to_submit = None
    for idx, prompt in enumerate(suggestions):
        with cols[idx]:
            if st.button(prompt, key=f"sugg_{idx}", use_container_width=True):
                prompt_to_submit = prompt

    st.markdown("---")

    # 3. Render Historical Messages
    for msg in st.session_state["messages"]:
        role = msg.get("role")
        with st.chat_message(role):
            if role == "user":
                st.markdown(msg.get("content", ""))
            else:
                # Assistant message rendering
                answer = msg.get("answer", "")
                status = msg.get("status", "success")
                citations = msg.get("citations", [])
                val = msg.get("citation_validation", {})
                tool_calls = msg.get("tool_calls", [])
                evidence = msg.get("retrieved_evidence", [])
                error = msg.get("error")

                st.markdown(answer)

                # Citations Badge Row
                if citations:
                    citation_html = " ".join([
                        f'<span class="citation-badge">{c}</span>' for c in citations
                    ])
                    st.markdown(f"**Supporting Citations:** {citation_html}", unsafe_allow_html=True)

                # Grounding Validation Warning if applicable
                if val and not val.get("is_valid", True):
                    unsupported = val.get("unsupported", [])
                    st.warning(f"⚠️ Grounding Warning: Identifiers {unsupported} were cited but not verified in retrieved evidence.")

                # Tools & Evidence Expander
                if tool_calls or evidence or error:
                    with st.expander(f"🔍 Audit Trail ({len(tool_calls)} tool calls dispatched)"):
                        if tool_calls:
                            st.markdown("**Tool Calls Executed:**")
                            for tc in tool_calls:
                                st.markdown(f"- `{tc.get('tool')}`: {tc.get('summary')}")
                        if error:
                            st.error(f"Execution Error: {error}")
                        if evidence:
                            st.markdown("**Retrieved Knowledge Graph Evidence:**")
                            st.json(evidence, expanded=False)

    # 4. Handle Chat Input
    user_input = st.chat_input("Ask a clinical query (e.g., 'What medications was P101 prescribed?')...")
    active_prompt = prompt_to_submit or user_input

    if active_prompt:
        # Append User Message
        st.session_state["messages"].append({
            "role": "user",
            "content": active_prompt
        })

        # Display User Message
        with st.chat_message("user"):
            st.markdown(active_prompt)

        # Format bounded conversation history for follow-up conversational context
        history = []
        for m in st.session_state["messages"][:-1]:
            role = m.get("role")
            content = m.get("content") or m.get("answer") or ""
            if role in ["user", "assistant"] and content:
                history.append({"role": role, "content": content})

        # Execute Clinical Query via Groq ReAct Engine
        with st.chat_message("assistant"):
            with st.spinner("Traversing Knowledge Graph & Synthesizing Clinical Response..."):
                try:
                    result = run_clinical_query_detailed(
                        user_prompt=active_prompt,
                        conversation_history=history,
                        selected_patient_id=selected_patient_id
                    )
                except Exception as ex:
                    result = {
                        "query": active_prompt,
                        "patient_id": selected_patient_id,
                        "status": "error",
                        "answer": f"System error while running query: {str(ex)}",
                        "citations": [],
                        "citation_validation": {"supported": [], "unsupported": [], "is_valid": True},
                        "tool_calls": [],
                        "retrieved_evidence": [],
                        "error": str(ex)
                    }

                # Display Assistant Answer
                st.markdown(result.get("answer", ""))

                citations = result.get("citations", [])
                if citations:
                    citation_html = " ".join([
                        f'<span class="citation-badge">{c}</span>' for c in citations
                    ])
                    st.markdown(f"**Supporting Citations:** {citation_html}", unsafe_allow_html=True)

                val = result.get("citation_validation", {})
                if val and not val.get("is_valid", True):
                    unsupported = val.get("unsupported", [])
                    st.warning(f"⚠️ Grounding Warning: Identifiers {unsupported} were cited but not verified in retrieved evidence.")

                tool_calls = result.get("tool_calls", [])
                evidence = result.get("retrieved_evidence", [])
                if tool_calls or evidence or result.get("error"):
                    with st.expander(f"🔍 Audit Trail ({len(tool_calls)} tool calls dispatched)"):
                        if tool_calls:
                            st.markdown("**Tool Calls Executed:**")
                            for tc in tool_calls:
                                st.markdown(f"- `{tc.get('tool')}`: {tc.get('summary')}")
                        if result.get("error"):
                            st.error(f"Execution Error: {result.get('error')}")
                        if evidence:
                            st.markdown("**Retrieved Knowledge Graph Evidence:**")
                            st.json(evidence, expanded=False)

        # Save Assistant Result to Session State
        st.session_state["messages"].append({
            "role": "assistant",
            "content": result.get("answer", ""),
            "answer": result.get("answer", ""),
            "status": result.get("status", "success"),
            "citations": citations,
            "citation_validation": val,
            "tool_calls": tool_calls,
            "retrieved_evidence": evidence,
            "error": result.get("error")
        })

        st.rerun()

import streamlit as st

def apply_custom_styles():
    """
    Injects custom CSS styling for a modern, clinical healthcare aesthetic.
    Navy (#0F2942 / #1E3A8A), Teal (#0D9488), White (#FFFFFF), and Neutral Grey (#F8FAFC, #E2E8F0).
    """
    st.markdown(
        """
        <style>
        /* Base typography & layout adjustments */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }

        /* Persistent Academic Disclaimer Banner */
        .academic-notice-banner {
            background-color: #F1F5F9;
            border-left: 4px solid #0D9488;
            color: #334155;
            padding: 8px 16px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 1.5rem;
            border-radius: 0 4px 4px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        /* Metric cards */
        .metric-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 16px 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            margin-bottom: 12px;
        }
        .metric-card-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748B;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .metric-card-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0F172A;
            line-height: 1.2;
        }
        .metric-card-sub {
            font-size: 0.8rem;
            color: #64748B;
            margin-top: 4px;
        }

        /* Citation Badge Pill */
        .citation-badge {
            display: inline-block;
            background-color: #E0F2FE;
            color: #0369A1;
            border: 1px solid #BAE6FD;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-right: 6px;
            margin-bottom: 4px;
            font-family: monospace;
        }

        /* Status Pills */
        .status-badge-success {
            display: inline-block;
            background-color: #DCFCE7;
            color: #15803D;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .status-badge-warning {
            display: inline-block;
            background-color: #FEF3C7;
            color: #B45309;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .status-badge-info {
            display: inline-block;
            background-color: #E0E7FF;
            color: #4338CA;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #F8FAFC;
            border-right: 1px solid #E2E8F0;
        }

        /* Header accents */
        h1, h2, h3 {
            color: #0F172A;
            font-weight: 700;
        }
        h1 {
            font-size: 1.8rem !important;
            margin-bottom: 0.5rem !important;
        }
        h2 {
            font-size: 1.35rem !important;
            margin-top: 1.25rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_academic_notice():
    """Renders the persistent unobtrusive academic notice."""
    st.markdown(
        """
        <div class="academic-notice-banner">
            <span>Academic demonstration | Synthetic hospital data | Not for clinical decision-making</span>
            <span style="color:#0D9488; font-weight:600;">Neo4j AuraDB • Groq ReAct RAG</span>
        </div>
        """,
        unsafe_allow_html=True
    )

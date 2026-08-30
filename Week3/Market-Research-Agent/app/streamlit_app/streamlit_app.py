import streamlit as st

from app.streamlit_app.components.state import init_state

st.set_page_config(
    page_title="Sightline — Competitor Research",
    page_icon=":material/travel_explore:",
    layout="wide",
)
init_state()

pages = [
    st.Page("app_pages/discovery.py", title="Discovery", icon=":material/search:", default=True),
    st.Page(
        "app_pages/research_progress.py",
        title="Research progress",
        icon=":material/network_intelligence:",
    ),
    st.Page("app_pages/briefing.py", title="Briefing", icon=":material/description:"),
]

st.navigation(pages).run()

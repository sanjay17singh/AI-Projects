import streamlit as st

st.set_page_config(page_title="AgentGate", page_icon=":material/verified_user:", layout="wide")

page = st.navigation(
    [
        st.Page("app_pages/dashboard.py", title="Dashboard", icon=":material/dashboard:"),
        st.Page("app_pages/new_evaluation.py", title="New evaluation", icon=":material/add_circle:"),
        st.Page("app_pages/run_details.py", title="Run details", icon=":material/timeline:"),
        st.Page("app_pages/human_review.py", title="Human review", icon=":material/fact_check:"),
        st.Page("app_pages/final_report.py", title="Final report", icon=":material/summarize:"),
        st.Page("app_pages/scenario_library.py", title="Scenario library", icon=":material/menu_book:"),
    ],
    position="sidebar",
)
page.run()

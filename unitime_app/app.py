"""Main Streamlit application entry point for Intelligent University Timetable Management System."""
import streamlit as st

from unitime_app.data_loader import load_dataset_statistics
from unitime_app.views import comparison, dashboard, generator, methodology, validation, viewer


def main():
    st.set_page_config(
        page_title="Intelligent University Timetable Management System",
        page_icon=":material/school:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    stats = load_dataset_statistics()

    st.sidebar.title("UniTime scheduler")
    st.sidebar.caption("Purdue University · Fall 2007 benchmark")

    pages = {
        "Dashboard": dashboard.render,
        "Generate timetable": generator.render,
        "View timetable": viewer.render,
        "Compare results": comparison.render,
        "Validate timetable": validation.render,
        "Methodology": methodology.render,
    }

    selected_page = st.sidebar.radio("Navigate", list(pages.keys()), index=0)

    st.sidebar.divider()
    st.sidebar.markdown(
        f"**Dataset**  \n"
        f"{stats['classes_count']:,} classes · {stats['rooms_count']:,} rooms  \n"
        f"ML ranker: logistic pipeline  \n"
        f"Hard checks: room and instructor"
    )

    pages[selected_page]()


if __name__ == "__main__":
    main()

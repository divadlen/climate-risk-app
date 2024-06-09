import streamlit as st



def main():
    # um not updating

    st.markdown("Loading user manual...")

    try:
        st.markdown("""
        <embed src="https://storage.googleapis.com/gecko-s3-public/trace/TRACE%20User%20Manual%20v1.2.pdf" width="100%" height="1000">
        """, unsafe_allow_html=True)
    except Exception as e:
        print(e)
        st.error(e)

    
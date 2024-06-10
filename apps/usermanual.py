import streamlit as st



def main():
    st.info('If the user manual is not being displayed properly here, you may view file at [this link](https://storage.googleapis.com/gecko-s3-public/trace/TRACE%20User%20Manual%20v1.2.pdf)')
    
    st.markdown("""
    <embed src="https://storage.googleapis.com/gecko-s3-public/trace/TRACE%20User%20Manual%20v1.2.pdf" width="100%" height="1000">
    """, unsafe_allow_html=True)

    


    
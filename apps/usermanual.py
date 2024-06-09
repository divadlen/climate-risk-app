import streamlit as st



def main():
    st.info('User manual not displaying for you? Try a different browser or go to [this link](https://storage.googleapis.com/gecko-s3-public/trace/TRACE%20User%20Manual%20v1.2.pdf)')
    
    st.markdown("""
    <embed src="https://storage.googleapis.com/gecko-s3-public/trace/TRACE%20User%20Manual%20v1.2.pdf" width="100%" height="1000">
    """, unsafe_allow_html=True)

    


    
import streamlit as st
import base64



def main():
    # # Path to your PDF file
    # file_path = 'resources/pdfs/TRACE User Manual v1.2.pdf'

    # # Convert your PDF to a base64 string
    # with open(file_path, "rb") as pdf_file:
    #     base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')

    # st.markdown(f"""
    # <embed src="data:application/pdf;base64,{base64_pdf} width="100%" height="900">
    # """, unsafe_allow_html=True)

    st.markdown("""
    <embed src="https://thomasmorestudies.org/wp-content/uploads/2020/09/Richard.pdf" width="100%" height="900">
    """, unsafe_allow_html=True)
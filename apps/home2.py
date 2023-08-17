import streamlit as st

def main():
  st.title('ttt')

  st.write(st.session_state['gdc'])
  st.write(st.secrets['abc'])
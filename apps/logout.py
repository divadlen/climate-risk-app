import streamlit as st    

def logoutPage():
    st.info(f"Currently logged in as: **{st.session_state['username']}**")
    st.warning('Are you sure you want to log out?')

    if st.button('Confirm Logout'):
      st.session_state["authenticated"] = None
      st.success('You have been logged out.')
      st.experimental_rerun()

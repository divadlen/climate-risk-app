import streamlit as st
import hydralit as hy

from app_config import run_app_config
import apps

st.set_page_config(
  page_title="Ex-stream-ly Cool App",
  page_icon="🧊",
  layout="wide",
  initial_sidebar_state="expanded",
  menu_items={
    'Get Help': 'https://www.extremelycoolapp.com/help',
    'Report a bug': "https://www.extremelycoolapp.com/bug",
    'About': "# This is a header. This is an *extremely* cool app!",
  }
)

#---Start app---#
def run_app():
  # Check if user is authenticated
  from apps.auth import AuthApp
  if not st.session_state.get("authenticated"):
    # Run authentication app
    AuthApp()
    return

  #---Load states and configurations---#
  st.snow()
  run_app_config()

  with st.sidebar:
    logout = st.button('Logout')
    if logout:
      st.session_state["authenticated"] = None
      st.experimental_rerun()

    qwe = st.text_input('QWE')

  #---Start Hydra instance---#
  over_theme = {'txc_inactive': '#FFFFFF', 'txc_active':'#A9DEF9'}
  navbar_theme = {'txc_inactive': '#FFFFFF','txc_active':'grey','menu_background':'white','option_active':'blue'}

  app = hy.HydraApp(
    title='Simple Multi-Page App',
    favicon="🐙",
    hide_streamlit_markers=False,
    use_banner_images=[
      None,
      "./resources/G1-long.png",
      None,
    ], 
    banner_spacing=[1,60,1],
    use_navbar=True, 
    navbar_sticky=False,
    navbar_animation=True,
    navbar_theme=over_theme,
  )

  #---Add apps from folder---#
  @app.addapp(is_home=True)
  def my_home(title='home'):
    hy.info('Hello from Home!')

  @app.addapp(title='The Best 2')
  def app2():
    hy.info('Hello from app 2')

  @app.addapp(title='The Best', icon="🥰")
  def app3():
    hy.info('Hello from app 3, A.K.A, The Best 🥰')

  @app.addapp(title='from app folder')
  def app4():
    from apps.home2 import main
    main()

  #---Optional, if you want to nest navigations---#
  complex_nav = {
    "Home": ['home'],
    "app folder": ['from app folder'],
    "bests": ['The Best', 'The Best 2']
  }

  app.run(complex_nav=complex_nav)

if __name__ == '__main__':
  run_app()
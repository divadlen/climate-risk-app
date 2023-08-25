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
  # st.snow()
  run_app_config()

  with st.sidebar:
    qwe = st.text_input('QWE')

  #---Start Hydra instance---#
  over_theme = {'txc_inactive': '#FFFFFF', 'txc_active':'#A9DEF9'}
  navbar_theme = {'txc_inactive': '#FFFFFF','txc_active':'grey','menu_background':'white','option_active':'blue'}

  st.image("./resources/G1-long.png", use_column_width=True, width=None)
  app = hy.HydraApp(
    hide_streamlit_markers=False,
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

  @app.addapp(title='from app folderr')
  def app4():
    from apps.home2 import main
    main()

  @app.addapp(title='Logout')
  def logout_button():
    from apps.logout import logoutPage
    logoutPage()

  @app.addapp(title='Great heatmap')
  def heatmapApp():
    from apps.heatmap import heatmapPage
    heatmapPage()

  @app.addapp(title='Graph connect')
  def barfiApp():
    from apps.barfi import barfiPage
    barfiPage()

  @app.addapp(title='Scope 1: Stationary Combustion')
  def s1scApp():
    from apps.s1sc_page import s1sc_Page
    s1sc_Page()

  #specify a custom loading app for a custom transition between apps, this includes a nice custom spinner
  from apps._loading import MyLoadingApp
  app.add_loader_app(MyLoadingApp(delay=0))

    
  #---Optional, if you want to nest navigations---#
  complex_nav = {
    "Home": ['home'],
    "Scope 1": ['Scope 1: Stationary Combustion'],
    "heat": ['Great heatmap'],
    "graph": ["Graph connect"],
    "app folder": ['from app folderr'],
    "bests": ['The Best', 'The Best 2'],
    "logout": ['Logout'],
  }

  app.run(complex_nav=complex_nav)

if __name__ == '__main__':
  run_app()
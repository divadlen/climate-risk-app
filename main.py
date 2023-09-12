import streamlit as st
import hydralit as hy

from PIL import Image
from app_config import run_app_config
import apps

st.set_page_config(
  page_title="Gecko Technologies Emission Calculation Service",
  page_icon="🧊",
  layout="wide",
  initial_sidebar_state="expanded",
  menu_items={
    'Get Help': 'https://www.geckointel.com',
    'Report a bug': "https://geckointel.com/contact-us",
    'About': "# Gecko Technologies. GHG Emission Calculation Service",
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

    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"], accept_multiple_files=False, help='CSV containinype transactions for S1: Stationary Combustion')


  #---Start Hydra instance---#
  over_theme = {'txc_inactive': '#FFFFFF', 'txc_active':'#004457'}
  navbar_theme = {'txc_inactive': '#FFFFFF','txc_active':'grey','menu_background':'#05F1E3','option_active':'#004457'}

  col1, col2, col3 = st.columns([1,2,1])
  with col2:
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

  @app.addapp(title='Data')
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

  @app.addapp(title='Risk Heatmap')
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

  @app.addapp(title='Scope 1: Mobile Combustion')
  def s1mcApp():
    from apps.s1mc_page import s1mc_Page
    s1mc_Page()

  @app.addapp(title='Scope 2: Indirect Emissions')
  def s2ieApp():
    from apps.s2ie_page import s2ie_Page
    s2ie_Page()

  @app.addapp(title='Scope 3: Value Chain')
  def s3vcApp():
    from apps.s3vc_page import s3vc_Page
    s3vc_Page()

  @app.addapp(title='Dash V1')
  def dashApp_v1():
    from apps.dash_v1 import dash_Page_v1
    dash_Page_v1()

  #specify a custom loading app for a custom transition between apps, this includes a nice custom spinner
  from apps._loading import MyLoadingApp
  app.add_loader_app(MyLoadingApp(delay=0))

    
  #---Optional, if you want to nest navigations---#
  complex_nav = {
    "Home": ['home'],
    "Emissions Calculator": ['Scope 1: Stationary Combustion', 'Scope 1: Mobile Combustion', 'Scope 2: Indirect Emissions', 'Scope 3: Value Chain'],
    "heat": ['Risk Heatmap'], 
    "Graphics": ["Data", "Dash V1"],
    #"app folder": ['from app folderr'],
    #"bests": ['The Best', 'The Best 2'],
    "logout": ['Logout'],
  }

  app.run(complex_nav=complex_nav)

if __name__ == '__main__':
  run_app()
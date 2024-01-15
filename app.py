import streamlit as st
from pages import *

#TODO: MANUAL CACHE RELOAD
#TODO: RESUMEN DE HORAS TRABAJADAS
#TODO: FECHA DURACION PROYECTO
#TODO: VALIDACION CREACION DE USUARIO
#TODO: ICONO CUANDO NO HAY NADA

st.set_page_config(layout="wide", page_title = "AAFO Projects", page_icon = "🌐")

try:
    assert st.secrets.get('NOTION_API_KEY'), "No se ha configurado la llave de Notion"
    assert st.secrets.get('TASK_DATABASE'), "No se ha configurado la base de datos de tareas"
    assert st.secrets.get('CLIENTS_DATABASE'), "No se ha configurado la base de datos de clientes"
except AssertionError as e:
    st.error(f"{e}, configura el secreto correspondiente")
    st.stop()

if st.session_state.get('css_classes') is None:
    with open('./style.html', 'r') as f:
        st.session_state.css_classes = f.read()

st.write(st.session_state.css_classes, unsafe_allow_html=True)
            
# Streamlit app
def main():
    if not st.session_state.get('login'):
        login_page()
    if st.session_state.get('login'):
        report_page()

if __name__ == '__main__':
    main()
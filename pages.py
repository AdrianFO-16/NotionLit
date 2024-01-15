import streamlit as st
from notion_utils import *
from hashlib import sha256
import pandas as pd

def get_report_data(project_id):
    tasks = get_project_tasks_pages(project_id)
    df = []
    for task in tasks:
        row = [find_title(task), find_date(task, 'Due'), find_status(task, 'Status'), find_priority(task, 'Priority'), find_hours(task, 'HorasUtilizadas')]
        df.append(row)
    df = pd.DataFrame(df, columns=['Titulo', "Fecha", 'Status', 'Prioridad', "Horas Trabajadas"])
    df.loc["Total", "Horas Trabajadas"] = df["Horas Trabajadas"].sum()
    df.loc[:, "Horas Trabajadas"] = df["Horas Trabajadas"].apply(format_hours) 
    df.replace(
        {'Status': 
         {'Not started': '<span class="keyword gray">No Iniciado</span>',
          'In progress': '<span class="keyword blue">En Progreso</span>',
          'Done': '<span class="keyword green">Completado</span>'
          },

          "Prioridad": {
              "Low": '<span class="keyword blue">Baja</span>',
              "Medium": '<span class="keyword yellow">Media</span>',
              "High": '<span class="keyword red">Alta</span>'
          }
          }, inplace=True)
    df.fillna('', inplace=True)
    df.replace('nan', '', inplace=True)
    return df.style.set_properties(**{'text-align': 'center'})


def logged_in(func):
    def wrapper():
        _, col = st.columns([1, 0.2], gap = "large")
        with col:
            st.button("Logout", on_click = lambda: st.session_state.clear())
        func()
    return wrapper

@logged_in
def report_page():
    st.session_state.projects = get_user_projects(st.session_state.user)
    st.sidebar.title("Proyectos")
    if not st.session_state.get('projects'):
        st.header("No hay nada por aca")
        st.write("No tienes proyectos asignados (aún), contacta a tu administrador o vuelve a intentar despues de un tiempo")
        return
    project = st.sidebar.selectbox("Selección", options = st.session_state.projects, format_func = lambda x: x.get('title'))
    report(project.get("object"), project.get('title'))
    

def report(project, title):
    icon = project.get('icon')
    completion = int((find_property(project, "Completion").get('rollup').get('number') or 0) * 100)
    project_name = title
    df = get_report_data(project.get('id'))
    HEADER = st.container()
    with HEADER:
        if icon.get('type') == 'emoji':
            icon = icon.get('emoji')
            if icon:
                st.write(f"<span style='font-size:100px'>{icon}</span>", unsafe_allow_html= True)
        elif icon.get('type') == 'external':
            icon = icon.get('external').get('url')
            if icon:
                st.image(icon, width=100)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"<h1>Reporte de Progreso {project_name}</h1>", unsafe_allow_html =True)
        with col2:
            st.write(f"<h3>{get_project_status_badge(project)} {completion:.0f}%</h3>", unsafe_allow_html=True)
            get_project_status_badge(project)
            st.progress(completion)
            if completion == 100:
                st.balloons()
    st.divider()
    BODY = st.container()
    with BODY:
        _, col, _ = st.columns([0.1, 1, 0.1], gap = "medium")
        with col:
            st.write(df.to_html(escape=False),  unsafe_allow_html = True)

@st.cache_data(ttl = 60, show_spinner=False)
def get_user_projects(user):
    print(f'id {user.get("id")[:10]} [...] user reloading projects . . .')
    projects = user.get('properties').get('projects').get('relation')
    notion_objects = list(map(lambda x: n_object(x.get('id'), 'pages'), projects))
    projects_object = [dict(id = project.get('id'), title = find_title(project), object = project) for project in notion_objects]
    return projects_object

def handle_login():
    if not st.session_state.get('username_input') or not st.session_state.get('password_input'):
        st.error("Usuario o contraseña vacios")
        return
    hashed = sha256(st.session_state.username_input.encode() + st.session_state.password_input.encode()).hexdigest()
    users = get_users(hashed)
    if len(users) == 0:
        st.error("Login Incorrecto")
        st.session_state.username_input = ''
        st.session_state.password_input = ''
    elif len(users) > 1:
        st.error("Error de autenticacion")
        st.session_state.username_input = ''
        st.session_state.password_input = ''
    else:
        st.session_state.login = True
        st.session_state.user = users[0]
        st.session_state.username_input = ''
        st.session_state.password_input = ''
    return

def handle_create_user():
    if not st.session_state.get('username_input') or not st.session_state.get('password_input'):
        st.error("Usuario o contraseña vacios")
        return
    hashed = sha256(st.session_state.username_input.encode() + st.session_state.password_input.encode()).hexdigest()
    st.session_state.created_user = (st.session_state.username_input, hashed)
    st.session_state.username_input = ''
    st.session_state.password_input = ''
    st.balloons()

def login_page():
    sidebar = st.sidebar.title("Login")
    with sidebar:
        options = ["Login", "Crea Usuario"]
        sidebar_select = st.selectbox("Pagina", options = list(range(len(options))), format_func=lambda x: options[x], index = 0)
    BODY = st.container()
    with BODY:
        _, col, _ = st.columns([0.1, 1, 0.1], gap = "medium")
        with col:
            if sidebar_select == 0:
                st.header("Login")
                form = st.form(key='login-form')
                with form:
                    st.text_input("Username", key = 'username_input')
                    st.text_input("Password", key = 'password_input', type="password")
                    st.form_submit_button("Login", on_click=handle_login)
            elif sidebar_select == 1:
                st.header("Crear Usuario")
                form = st.form(key='create-user-form')
                with form:
                    st.text_input("Username", key = 'username_input')
                    st.text_input("Password", key = 'password_input', type="password")
                    st.form_submit_button("Crear Usuario", on_click=handle_create_user)
                if st.session_state.get('created_user'):
                    st.success("Usuario creado con exito")
                    st.write(f"Usuario: {st.session_state.created_user[0]}")
                    st.write(f"Clave: {st.session_state.created_user[1]}")
                    st.write("Envía esta información a tu administrador para que te de acceso")
                    st.session_state.created_user = None
            else:
                return
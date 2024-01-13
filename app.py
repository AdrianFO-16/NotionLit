import streamlit as st
import requests
import pandas as pd
from hashlib import sha256
TTL = 60#segs

#TODO: MANUAL CACHE RELOAD

st.set_page_config(layout="wide", page_title = "AAFO Projects", page_icon = "🌐")

try:
    assert st.secrets.get('NOTION_API_KEY'), "No se ha configurado la llave de Notion"
    assert st.secrets.get('TASK_DATABASE'), "No se ha configurado la base de datos de tareas"
    assert st.secrets.get('CLIENTS_DATABASE'), "No se ha configurado la base de datos de clientes"
except AssertionError as e:
    st.error(f"{e}, configura el secreto correspondiente")
    st.stop()

st.write("""
<style>
.keyword {
    font-weight: bold;
    font-size: 0.8rem;
    color: white;
    display: inline-block;
    padding: 0.1rem 0.3rem;
    border-radius: 0.8rem;
}
.badge {
    font-size: 1.2rem;
    color: white;
    display: inline-block;
    padding: 0.3rem 0.5rem;
    border-radius: 0.8rem;
}
.blue {
    background-color: #00478c;
}
.green {
    background-color: #008c15;
}
.yellow {
    background-color: #8c7900;
}
.red{
    background-color: #8c0000;
}
.gray{
    background-color: #8c8c8c;
}
         
table{
    width:100%;
}

table th {
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


def n_query(id, query_obj):
    req = requests.post(f'https://api.notion.com/v1/databases/{id}/query', json = query_obj, headers={"Authorization": f"Bearer {st.secrets.NOTION_API_KEY}", "Notion-Version": "2022-06-28"})
    if not bool(req):
        raise Exception(f"Invalid Query: {req.json().get('message')}")
    return req.json()

def n_object(id, object):
    req = requests.get(f'https://api.notion.com/v1/{object}/{id}', headers={"Authorization": f"Bearer {st.secrets.NOTION_API_KEY}", "Notion-Version": "2022-06-28"})
    if not bool(req):
        raise Exception("Invalid Query")
    return req.json()

@st.cache_data(ttl = TTL, show_spinner=False)
def get_project_tasks_pages(project_id):
    query_obj = {
        "filter": {
            "property": "project",
            "relation": {
                "contains": project_id
            }
        },
        "sorts": [
            {
                "property":"Due", "direction":"ascending"
            }
        ]
    } 
    print(f'id {project_id[:10]} [...] reloading project tasks . . .')
    data =  n_query(st.secrets.TASK_DATABASE, query_obj)
    tasks = tuple(filter(lambda x: x.get('object') == 'page', data.get('results')))
    return tasks

def get_users(hashed):
    search_obj = {
        "filter": {"and" : [
            {
            "property": "User",
            "rich_text": {
            "equals": st.session_state.get('username_input')
                }
            },
            {
            "property": "AuthHash",
            "rich_text": {
            "equals": hashed
                }
            }
        ]
        }
    }
    data = n_query(st.secrets.get('CLIENTS_DATABASE'), search_obj)
    users = tuple(filter(lambda x: x.get('object') == 'page', data.get('results')))
    return users

def get_tasks_db():
    return n_object(st.secrets.TASK_DATABASE, 'databases')

def find_title(d):
    d = find_dict_with_key_value(d, 'id', 'title')
    return d.get('title')[0].get('text').get('content')

def find_property(d, prop, treatment = lambda x: x):
    d = d.get('properties').get(prop)
    return treatment(d)

def find_status(d, prop):
    prop = find_property(d, prop, lambda x: x.get('status'))
    if prop != None:
        return prop.get('name')
    return None

def find_priority(d, prop):
    prop = find_property(d, prop, lambda x: x.get('select'))
    if prop != None:
        return prop.get('name')
    return None

def find_property_options(d, prop, type):
    return find_property(d, prop, lambda x: x.get(type).get('options'))

def find_dict_with_key_value(d, key, value):
    if isinstance(d, dict):
        if d.get(key) == value:
            return d
        else:
            for v in d.values():
                result = find_dict_with_key_value(v, key, value)
                if result:
                    return result
    elif isinstance(d, (list, tuple)):
        for item in d:
            result = find_dict_with_key_value(item,key, value)
            if result:
                return result
    return None

def find_date(d, prop):
    prop = find_property(d, prop, lambda x: x.get('date'))
    if prop != None:
        start =  prop.get('start')
        end  =  prop.get('end')
        if not end or end == start:
            return start
        return start if start == end else f"{start} ➡️ {end}"
    return None


def get_project_status_badge(project):
        match find_status(project, 'Status'):
            case 'Planning':
                return '<span class="badge gray">En Planeación</span>'
            case 'In Progress':
                return '<span class="badge blue">En Progreso</span>'
            case 'Done':
                return '<span class="badge green">Completado</span>'
            case _:
                return '<span class="badge gray">Finalizado</span>'


def get_report_data(project_id):
    tasks = get_project_tasks_pages(project_id)
    df = []
    for task in tasks:
        row = [find_title(task), find_date(task, 'Due'), find_status(task, 'Status'), find_priority(task, 'Priority')]
        df.append(row)

    df = pd.DataFrame(df, columns=['Titulo', "Fecha", 'Status', 'Priority'])
    df.replace(
        {'Status': 
         {'Not started': '<span class="keyword gray">No Iniciado</span>',
          'In progress': '<span class="keyword blue">En Progreso</span>',
          'Done': '<span class="keyword green">Completado</span>'
          },

          "Priority": {
              "Low": '<span class="keyword blue">Baja</span>',
              "Medium": '<span class="keyword yellow">Media</span>',
              "High": '<span class="keyword red">Alta</span>'
          }
          }, inplace=True)
    df.fillna('', inplace=True)
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
            st.write(f"<span style='font-size:100px'>{icon.get('emoji')}</span>", unsafe_allow_html= True)
        elif icon.get('type') == 'external':
            st.image(icon.get('external').get('url'), width=100)
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

@st.cache_data(ttl = TTL, show_spinner=False)
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
            
# Streamlit app
def main():
    if not st.session_state.get('login'):
        login_page()
    if st.session_state.get('login'):
        report_page()

if __name__ == '__main__':
    main()
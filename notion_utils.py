import requests
import streamlit as st

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

def find_hours(d, prop):
    return find_property(d, prop, lambda x: x.get('number'))

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

def format_hours(x):
    if x is None:
        return None
    elif x % 1 == 0:
        return f"{x:.0f}"
    else:
        return f"{x:.2f}"

@st.cache_data(ttl = 60, show_spinner=False)
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
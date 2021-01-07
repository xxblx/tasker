
class SelectQueries:
    password_auth = 'SELECT password FROM tasker.users WHERE username = %s'
    token_auth = """
SELECT
    u.user_id, u.username, t.token_verify
FROM
    tasker.tokens t INNER JOIN tasker.users u on t.user_id = u.user_id
WHERE
    t.token_select = %s and t.expires_in >= extract(epoch from now())
"""
    token_renew = """
SELECT
    u.username, t.token_verify, t.token_id
FROM
     tasker.tokens t INNER JOIN tasker.users u on t.user_id = u.user_id
WHERE
    t.token_select = %s and t.token_renew = %s
"""
    # Check access to the project
    # If the project doesn't exists return nothing
    project_access = """
SELECT
    projects.project_id, pu.role
FROM
    tasker.projects
    INNER JOIN
    tasker.projects_users pu on projects.project_id = pu.project_id
WHERE 
    pu.user_id = %s and projects.project_pub_id = %s
"""
    # If folder doesn't exists or user doesn't have access to it
    # return nothing
    project_folder_access = """
SELECT
    projects.project_id, folders.folder_id, pu.role
FROM
    tasker.projects_users pu
    INNER JOIN
    tasker.projects on pu.project_id = projects.project_id
    
    INNER JOIN
    tasker.folders on pu.project_id = folders.project_id
WHERE
    pu.user_id = %s 
    and projects.project_pub_id = %s
    and folders.folder_pub_id = %s
"""
    # If task doesn't exists or user doesn't have access to it
    # return nothing
    project_folder_task_access = """
SELECT
    projects.project_id, folders.folder_id, tasks.task_id, pu.role
FROM
    tasker.projects_users pu
    INNER JOIN
    tasker.projects on pu.project_id = projects.project_id
    
    INNER JOIN
    tasker.folders on pu.project_id = folders.project_id
    
    INNER JOIN
    tasker.tasks on pu.project_id = tasks.project_id
WHERE
    pu.user_id = %s 
    and projects.project_pub_id = %s
    and folders.folder_pub_id = %s
    and tasks.task_pub_id = %s
"""
    # List projects available for a user
    projects = """
SELECT 
    project_pub_id id, role, title, description
FROM
    tasker.projects_users pu       
    INNER JOIN tasker.projects on pu.project_id = projects.project_id
WHERE
    pu.user_id = %s
"""
    # List folders in a project
    folders = """
SELECT 
    f.folder_pub_id id, f.title
FROM 
    tasker.folders f INNER JOIN tasker.projects p on f.project_id = p.project_id
WHERE 
    p.project_id = %s
"""
    # List tasks in a folder
    tasks_by_folder = """
SELECT
    t.task_pub_id id,
    p.project_pub_id project_id,
    f.folder_pub_id folder_id,
    t.title,
    t.datetime_from,
    t.datetime_due,
    t.edited
FROM
    tasker.tasks t 
    INNER JOIN tasker.folders f on t.folder_id = f.folder_id
    INNER JOIN tasker.projects p on t.project_id = p.project_id
WHERE
    t.project_id = %s and f.folder_pub_id = %s
"""
    # List tasks in a project
    tasks_by_project = """
SELECT
    p.project_pub_id project_id,
    f.folder_pub_id folder_id,
    t.task_pub_id id,
    t.title,
    t.datetime_from,
    t.datetime_due,
    t.edited
FROM
    tasker.tasks t 
    INNER JOIN tasker.folders f on t.folder_id = f.folder_id
    INNER JOIN tasker.projects p on t.project_id = p.project_id
WHERE
    t.project_id = %s
"""
    # Get project details
    # TODO: remove user_id because by the time of the query execution
    # TODO: the ApiHandler has checked the user access already
    project = """
SELECT 
    projects.project_pub_id id,
    projects.title, 
    projects.description,
    json_agg(json_build_object(
        'username', users.username, 
        'role', pu.role
    )) users
FROM
    tasker.projects_users pu
    INNER JOIN
    tasker.projects on pu.project_id = projects.project_id
    
    INNER JOIN
    tasker.users on pu.user_id = users.user_id
WHERE
    pu.user_id = %s and projects.project_pub_id = %s
GROUP BY
    projects.project_pub_id,
    projects.title, 
    projects.description
"""


class InsertQueries:
    add_user = """
INSERT INTO tasker.users(username, password) VALUES(%s, %s) RETURNING user_id
"""
    add_project = """
INSERT INTO tasker.projects(title, description) VALUES(%s, %s) 
RETURNING project_id, project_pub_id
"""
    add_folder = """
INSERT INTO tasker.folders(folder_pub_id, title, project_id)
VALUES(nextval('tasker.{seq}'), %s, %s)
RETURNING folder_id, folder_pub_id
"""
    add_task = """
INSERT INTO tasker.tasks(
    task_pub_id, title, description, datetime_from, datetime_due,
    user_id, project_id, folder_id
)
VALUES(nextval('tasker.{seq}'), %s, %s, %s, %s, %s, %s, %s)
RETURNING task_id, task_pub_id
"""
    add_user_project = """
INSERT INTO tasker.projects_users(project_id, user_id, role) VALUES(%s, %s, %s)
"""
    tokens = """
INSERT INTO 
    tasker.tokens(token_select, token_verify, token_renew, expires_in, user_id)
SELECT %s, %s, %s, CURRENT_TIMESTAMP + '{}'::INTERVAL, user_id
FROM tasker.users
WHERE username = %s
RETURNING CAST(FLOOR(EXTRACT(EPOCH FROM expires_in)) as INT)
"""


class InsertQueries:
    add_user = """
INSERT INTO tasker.users(username, password) VALUES(%s, %s) RETURNING user_id
"""
    add_project = """
INSERT INTO tasker.projects(title, description) VALUES(%s, %s) 
RETURNING project_id
"""
    add_folder = """
INSERT INTO tasker.folders(folder_pub_id, title, project_id)
VALUES(nextval('tasker.{seq}'), %s, %s)
"""
    add_user_project = """
INSERT INTO tasker.projects_users(project_id, user_id, role) VALUES(%s, %s, %s)
"""
    tokens = """
INSERT INTO 
    tasker.tokens(token_select, token_verify, token_renew, expires_in, user_id)
SELECT
    %s, %s, %s, %s, user_id
FROM
    tasker.users
WHERE
    username = %s
"""

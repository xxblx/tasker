
class UpdateQueries:
    display_name = """
UPDATE tasker.users SET display_name = %s WHERE username = %s
"""
    role_global = 'UPDATE tasker.users SET role_global = %s WHERE username = %s'
    password = 'UPDATE tasker.users SET password = %s WHERE username = %s'
    task = 'UPDATE tasker.tasks SET {} WHERE task_id = %(task_id)s'
    folder = 'UPDATE tasker.folders SET title = %s WHERE folder_id = %s'

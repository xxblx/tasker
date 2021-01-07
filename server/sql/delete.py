
class DeleteQueries:
    delete_user = 'DELETE FROM tasker.users WHERE username = %s'
    delete_tokens = 'DELETE FROM tasker.tokens WHERE token_id = %s'
    task = 'DELETE FROM tasker.tasks WHERE task_id = %s'


import os

def patch_views():
    file_path = 'activity/schedular/views.py'
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    with open(file_path, 'r') as f:
        content = f.read()

    # Target blocks for create_recurring_task and create_routine_task
    # Note: These use 10 spaces for if and 14 for task = ...
    
    target = """          if serializer.is_valid():
              task = serializer.save(project=project)

              user = request.user
              if user.role != 'ADMIN':
                  task.status = 'PENDING_APPROVAL'
                  task.save()
                  ApprovalRequest.objects.create(
                      reference_type='TASK',
                      reference_id=task.id,
                      approval_type='CREATION',
                      requested_by=user,
                      request_data=serializer.data
                  )"""

    replacement = """          if serializer.is_valid():
              with transaction.atomic():
                  task = serializer.save(project=project)

                  user = request.user
                  if user.role != 'ADMIN':
                      task.status = 'PENDING_APPROVAL'
                      task.save()
                      ApprovalRequest.objects.create(
                          reference_type='TASK',
                          reference_id=task.id,
                          approval_type='CREATION',
                          requested_by=user,
                          request_data=serializer.data
                      )"""

    if target in content:
        print("Found target block. Patching...")
        content = content.replace(target, replacement)
        with open(file_path, 'w') as f:
            f.write(content)
        print("Patch applied successfully.")
    else:
        # Try again with different spacing for the blank line
        target_alt = target.replace('\n\n', '\n          \n')
        if target_alt in content:
             print("Found target block (alt). Patching...")
             content = content.replace(target_alt, replacement)
             with open(file_path, 'w') as f:
                 f.write(content)
             print("Patch applied successfully (alt).")
        else:
             print("Target block not found in views.py.")

if __name__ == '__main__':
    patch_views()

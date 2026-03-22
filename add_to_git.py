import os
import subprocess
import sys

def add_folder_to_git(folder_path, commit_message="Add new folder to repository"):
    """
    Adds a folder to the git repository, commits, and pushes the changes.
    """
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return

    try:
        # Step 1: Add the folder to git
        print(f"Adding '{folder_path}' to git...")
        subprocess.run(["git", "add", folder_path], check=True)

        # Step 2: Commit the changes
        print(f"Committing changes...")

        # To avoid committing other untracked/modified changes (if any),
        # only check if there are staged changes to commit.
        status = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
        if not status.stdout.strip():
            print("No new staged changes to commit for this folder. It might be empty or already tracked.")
            return

        subprocess.run(["git", "commit", "-m", commit_message], check=True)

        # Step 3: Push to the remote repository
        print("Pushing to remote repository...")
        try:
            subprocess.run(["git", "push"], check=True)
            print(f"Successfully added '{folder_path}' to the remote repository!")
        except subprocess.CalledProcessError:
            print("Warning: 'git push' failed. You might need to set the upstream branch manually.")
            print("For example: git push --set-upstream origin <branch-name>")
            print("The folder has successfully been added and committed locally.")
            return

    except subprocess.CalledProcessError as e:
        print(f"A git command failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Get folder path from command line argument if provided, otherwise ask for input
    if len(sys.argv) > 1:
        folder_to_add = sys.argv[1]
    else:
        try:
            folder_to_add = input("Enter the name or path of the folder you want to add: ")
        except EOFError:
            print("\nNo input provided. Exiting.")
            sys.exit(1)

    add_folder_to_git(folder_to_add)

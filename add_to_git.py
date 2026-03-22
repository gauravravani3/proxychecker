import os
import subprocess
import sys
import shutil
import urllib.parse

def is_remote_git_url(path):
    """
    Checks if a given string looks like a remote git URL.
    """
    return path.startswith("http://") or path.startswith("https://") or path.startswith("git@")

def get_repo_name_from_url(url):
    """
    Extracts the repository name from a git URL.
    """
    if url.endswith(".git"):
        url = url[:-4]

    if url.startswith("git@"):
        # e.g. git@github.com:user/repo -> repo
        return url.split("/")[-1]
    else:
        # e.g. https://github.com/user/repo -> repo
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        if path.startswith("/"):
            path = path[1:]
        return path.split("/")[-1]

def is_subpath(path, base_path):
    """
    Returns True if path is a subpath of base_path.
    """
    try:
        rel = os.path.relpath(path, base_path)
        return not rel.startswith("..") and not rel == ".."
    except ValueError:
        # On Windows, ValueError is raised if paths are on different drives
        return False

def clone_repo(url, destination_folder=None):
    """
    Clones a git repository into the current directory or the specified folder.
    Returns the path to the cloned repository.
    """
    repo_name = get_repo_name_from_url(url)
    if not destination_folder:
        destination_folder = repo_name

    if os.path.exists(destination_folder):
        print(f"Directory '{destination_folder}' already exists.")
        if os.path.isdir(os.path.join(destination_folder, ".git")):
            print(f"It seems to be a git repository already. We will use the existing folder.")
            return destination_folder
        else:
            print(f"Error: '{destination_folder}' exists but is not a git repository. Cannot clone into it.")
            return None

    try:
        print(f"Cloning '{url}' into '{destination_folder}'...")
        subprocess.run(["git", "clone", url, destination_folder], check=True)
        return destination_folder
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository: {e}")
        return None

def add_folder_to_git(repo_path_or_url, folder_path, commit_message="Add new folder to repository"):
    """
    Adds a folder to the git repository, commits, and pushes the changes.
    The folder will be copied into the repository if it is not already inside it.
    """
    if is_remote_git_url(repo_path_or_url):
        # It's a remote URL, we need to clone it first
        repo_path = clone_repo(repo_path_or_url)
        if not repo_path:
            return # Cloning failed
    else:
        repo_path = repo_path_or_url

    if not os.path.exists(repo_path):
        print(f"Error: Repository path '{repo_path}' does not exist.")
        return

    # Check if the repo path is actually a git repository
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        print(f"Error: '{repo_path}' is not a valid git repository (missing .git folder).")
        return

    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return

    # If the folder is outside the repository, copy it inside the repository first.
    abs_repo_path = os.path.abspath(repo_path)
    abs_folder_path = os.path.abspath(folder_path)

    if not is_subpath(abs_folder_path, abs_repo_path):
        folder_name = os.path.basename(abs_folder_path)
        destination_path = os.path.join(abs_repo_path, folder_name)

        print(f"Folder '{folder_path}' is outside the repository.")
        print(f"Copying it to '{destination_path}'...")
        try:
            if os.path.exists(destination_path):
                print(f"Error: A file/folder named '{folder_name}' already exists in the repository.")
                return
            # Copy directory tree
            if os.path.isdir(abs_folder_path):
                shutil.copytree(abs_folder_path, destination_path)
            else:
                shutil.copy2(abs_folder_path, destination_path)

            # Update folder_path to point to the new location inside the repo
            folder_path = destination_path
        except Exception as e:
            print(f"Failed to copy folder: {e}")
            return

    # Path of the folder relative to the repository root for git commands
    rel_folder_path = os.path.relpath(folder_path, repo_path)

    try:
        # Step 1: Add the folder to git
        print(f"Adding '{rel_folder_path}' to git...")
        subprocess.run(["git", "add", rel_folder_path], cwd=repo_path, check=True)

        # Step 2: Commit the changes
        print(f"Committing changes...")

        # To avoid committing other untracked/modified changes (if any),
        # only check if there are staged changes to commit.
        status = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=repo_path, capture_output=True, text=True)
        if not status.stdout.strip():
            print("No new staged changes to commit for this folder. It might be empty or already tracked.")
            return

        subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_path, check=True)

        # Step 3: Push to the remote repository
        print("Pushing to remote repository...")
        try:
            subprocess.run(["git", "push"], cwd=repo_path, check=True)
            print(f"Successfully added '{rel_folder_path}' to the remote repository!")
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
    try:
        # Ask for the repository path
        print("Enter the path to your git repository or its remote URL (leave empty for current folder): ", end="")
        repo_path = input().strip()
        if not repo_path:
            repo_path = "."

        # Ask for the folder to add
        print("Enter the name or path of the folder you want to add: ", end="")
        folder_to_add = input().strip()
        if not folder_to_add:
            print("No folder provided. Exiting.")
            sys.exit(1)

        add_folder_to_git(repo_path, folder_to_add)

    except EOFError:
        print("\nNo input provided. Exiting.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nProcess interrupted. Exiting.")
        sys.exit(1)

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

def add_folder_to_git(repo_path, folder_path, commit_message=None):
    """
    Adds a single folder to the git repository, commits, and pushes the changes.
    The folder will be copied into the repository if it is not already inside it.
    """
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist. Skipping.")
        return

    # If the folder is outside the repository, copy it inside the repository first.
    abs_repo_path = os.path.abspath(repo_path)
    abs_folder_path = os.path.abspath(folder_path)
    folder_name = os.path.basename(abs_folder_path)

    if not is_subpath(abs_folder_path, abs_repo_path):
        destination_path = os.path.join(abs_repo_path, folder_name)

        print(f"Folder '{folder_name}' is outside the repository.")
        print(f"Copying it to '{destination_path}'...")
        try:
            if os.path.exists(destination_path):
                print(f"Warning: A file/folder named '{folder_name}' already exists in the repository. It will be overwritten/updated.")
                if os.path.isdir(destination_path):
                    shutil.rmtree(destination_path)
                else:
                    os.remove(destination_path)

            # Copy directory tree
            if os.path.isdir(abs_folder_path):
                shutil.copytree(abs_folder_path, destination_path)
            else:
                shutil.copy2(abs_folder_path, destination_path)

            # Update folder_path to point to the new location inside the repo
            folder_path = destination_path
        except Exception as e:
            print(f"Failed to copy folder '{folder_name}': {e}")
            return

    # Path of the folder relative to the repository root for git commands
    rel_folder_path = os.path.relpath(folder_path, repo_path)

    if commit_message is None:
        commit_message = f"Add {folder_name} to repository"

    try:
        # Step 1: Add the folder to git
        print(f"Adding '{rel_folder_path}' to git staging area...")
        subprocess.run(["git", "add", rel_folder_path], cwd=repo_path, check=True)

        # Step 2: Commit the changes
        status = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=repo_path, capture_output=True, text=True)
        if not status.stdout.strip():
            print(f"No new staged changes to commit for '{folder_name}'. It might be empty or already tracked.")
            return

        print(f"Committing changes for '{folder_name}'...")
        subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_path, check=True)

        # Step 3: Push to the remote repository
        print(f"Pushing '{folder_name}' to remote repository...")
        try:
            subprocess.run(["git", "push"], cwd=repo_path, check=True)
            print(f"Successfully added and pushed '{folder_name}'!\n")
        except subprocess.CalledProcessError:
            print("Warning: 'git push' failed. You might need to set the upstream branch manually.")
            print("For example: git push --set-upstream origin <branch-name>")
            print(f"'{folder_name}' has successfully been added and committed locally.\n")

    except subprocess.CalledProcessError as e:
        print(f"A git command failed for '{folder_name}': {e}")
    except Exception as e:
        print(f"An error occurred for '{folder_name}': {e}")


def process_folders(repo_path_or_url, paths):
    """
    Clones the repo if necessary, then loops through the provided paths
    and adds them one by one.
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

    # Add each folder one by one
    print("\n--- Starting upload process ---")
    for path in paths:
        path = path.strip()
        if path:
            print(f"\nProcessing '{path}'...")
            add_folder_to_git(repo_path, path)

if __name__ == "__main__":
    try:
        # Ask for the repository path
        print("Enter the path to your git repository or its remote URL (leave empty for current folder): ", end="")
        repo_input = input().strip()
        if not repo_input:
            repo_input = "."

        print("\nHow would you like to provide the folders to upload?")
        print("1. Provide a single parent directory containing all the folders you want to upload.")
        print("2. Provide multiple folder paths separated by a comma (,).")
        choice = input("Enter 1 or 2: ").strip()

        folders_to_add = []

        if choice == '1':
            parent_dir = input("Enter the path of the parent directory: ").strip()
            if os.path.isdir(parent_dir):
                # List all items in the parent directory
                for item in os.listdir(parent_dir):
                    item_path = os.path.join(parent_dir, item)
                    # Only add directories (or you can remove this check if you want files too)
                    if os.path.isdir(item_path):
                        folders_to_add.append(item_path)

                if not folders_to_add:
                    print("No folders found in the specified parent directory.")
                    sys.exit(0)
                else:
                    print(f"Found {len(folders_to_add)} folders to upload.")
            else:
                print("Invalid parent directory.")
                sys.exit(1)
        else:
            paths_input = input("Enter the names or paths of the folders, separated by commas:\n").strip()
            if not paths_input:
                print("No folders provided. Exiting.")
                sys.exit(1)
            folders_to_add = [p.strip() for p in paths_input.split(',')]

        process_folders(repo_input, folders_to_add)
        print("\nAll tasks completed!")

    except EOFError:
        print("\nNo input provided. Exiting.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nProcess interrupted. Exiting.")
        sys.exit(1)

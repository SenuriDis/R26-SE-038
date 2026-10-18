from src.github.repo_cloner import clone_repository

repo_url = "https://github.com/pallets/flask.git"

path = clone_repository(repo_url)

print("Repository cloned successfully!")
print(path)


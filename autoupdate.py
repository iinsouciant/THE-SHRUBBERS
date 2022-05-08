from git import Git, Repo
import requests
from pathlib import Path

# initializing test URL
url = "https://www.geeksforgeeks.org"
file = Path('shrubber_main.py')
myRepoDir = file.parent.absolute()
timeout = 10

try:
    # requesting URL
    request = requests.get(url, timeout=timeout)
    print("Internet is on")

    resetter = Repo(myRepoDir)
    myRepo = Git(myRepoDir)
    # revert local unsaved changes
    resetter.git.reset('--hard')
    # get latest commit
    myRepo.fetch()
    myRepo.pull('origin', 'main')
    print('pulled latest program version')
    
except (requests.ConnectionError, requests.Timeout) as exception:
    print("Internet is off")

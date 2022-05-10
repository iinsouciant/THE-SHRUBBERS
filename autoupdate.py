from git import Git, Repo
import requests
from pathlib import Path
from os import system
from sys import argv

# initializing test URL
url = "https://www.geeksforgeeks.org"
file = Path('shrubber_main.py')
myRepoDir = file.parent.absolute()
timeout = 10

for _ in range(3):
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
        break
    
    except (requests.ConnectionError, requests.Timeout) as exception:
        print("Internet is off")

try:
    if argv[1] == '--no-shrub':
        pass
except (IndexError, Exception) as e:
    system('python3 shrubber_main.py')
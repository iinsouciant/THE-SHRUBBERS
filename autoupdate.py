from git import Git, Repo
import requests
from os import system, getcwd
from sys import argv

# initializing test URL
url = "https://www.geeksforgeeks.org"
myRepoDir = getcwd()
file = myRepoDir + '\shrubber_main.py'
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

shrub = True
try:
    for myArg in argv:
        if myArg == '--no-shrub':
            shrub = False
except (IndexError, Exception) as e:
    system(f'python3 {file}')
if shrub:
    system(f'python3 {file}')
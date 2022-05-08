import git
import requests

# initializing test URL
url = "https://www.geeksforgeeks.org"
#shrubRepoDir = '/home/pi/THE-SHRUBBERS'
myRepoDir = '/Users/sands/OneDrive/Documents/School/SJSU/Senior project - Urban or Vertical Farming/Shrubbers Repository/THE-SHRUBBERS-1'
timeout = 10

try:
    # requesting URL
    request = requests.get(url, timeout=timeout)
    print("Internet is on")

    # get latest commit
    #shrubRepo = Repo(shrubRepoDir)
    #assert not shrubRepo.bare
    myRepo = git.Git(myRepoDir)
    myRepo.fetch()
    myRepo.pull('origin', 'main')
    print('pulled latest program version')
    
except (requests.ConnectionError, requests.Timeout) as exception:
    print("Internet is off")

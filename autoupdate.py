from git import Repo

shrubRepoDir ='/home/pi/THE-SHRUBBERS'

shrubRepo = Repo(shrubRepoDir)
assert not shrubRepo.bare

shrubRepo.config_reader()             # get a config reader for read-only access
with shrubRepo.config_writer():       # get a config writer to change configuration
    pass                         # call release() to be sure changes are written and locks are released


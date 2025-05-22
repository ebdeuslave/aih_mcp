import os

def autoPush(commitMsg):
   print(os.system(f"git add . && git commit -m '{commitMsg}' && git push --force"))
   
   
autoPush("isolate stores to .env")
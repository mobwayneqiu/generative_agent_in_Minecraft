from mcrcon import MCRcon

with MCRcon("127.0.0.1", "123456") as mcr:
  mcr.command(f"time set 1000")
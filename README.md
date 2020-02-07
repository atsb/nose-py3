# nose-py3
The original nose for nicer testing, converted to Python 3, cleaned and maintained

This is a drop-in replacement for 'nose'.

# install
pip install nose-py3

# notes
* plugins depending on python2 won't work as the code has been changed to be python3 compatible by default (python2 code has been removed).
* currently pycharm won't work with it (if you use it's own runner).  I'm working on making it compatible (it is because I removed Skip and Deprecated) as part of my modernising, I had no idea pycharm expects these (it's a pycharm bug IMO).

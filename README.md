# Migration to CodeBerg
Nose-py3 has migrated to EU-based CodeBerg!
https://codeberg.org/atsb/nose-py3

No further developments will be done here and the repo will be closed on GitHub in 6 months.

# nose-py3
The original nose for nicer testing, converted to Python 3, cleaned and maintained

This is a drop-in replacement for 'nose'.

# install
python3 -m pip install nose-py3

# notes
* plugins depending on python2 won't work as the code has been changed to be python3 compatible by default (python2 code has been removed).
* currently pycharm won't work with it (if you use it's own runner).  All errors that it had thrown have been fixed, now it simply refuses to find any tests.  Commandline usage still works, I consider this a pycharm bug.

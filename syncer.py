#!/usr/bin/python3
import threading
import subprocess
from pprint import pprint
import os
from optparse import OptionParser


REPOSITORIES = ['kernelight', 'usrlight', 'nvme-host']
WORKSPACE = os.environ.get('WORKSPACE_TOP', None)


class Syncer(object):
    err_dict = {}
    parser = None
    options = None

    @classmethod
    def _run_cmd(cls, cmd):
        print("*** Running: %s" % cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, encoding='utf8')
        out = p.communicate()
        if cls.options.verbose:
            print("\nOUTPUT:\n")
            while p.poll() is None:
                print(p.stdout.readline())
        return p.returncode, out

    @classmethod
    def build_repo(cls, name):
        print("Building %s" % name)
        dir_path = os.path.join(WORKSPACE, name)
        assert os.path.exists(dir_path), "No such directory %s" % dir_path
        cmd = "cd %s && dockerize make" % dir_path
        if os.path.exists(os.path.join(dir_path, "Makefile.lb")):
            cmd += " -f Makefile.lb"
        rc, out = cls._run_cmd(cmd)
        if rc != 0:
            global err_dict
            err_dict[name] = out


    @classmethod
    def run(cls):
        cls.init()
        assert WORKSPACE, "Couldn't find workspace env variable"
        rc, out = cls._run_cmd("cd %s && repo sync" % WORKSPACE)
        assert rc == 0, "\nFailed to run 'repo sync'"
        threads_list = []
        for repo in REPOSITORIES:
            t = threading.Thread(target=cls.build_repo, args=(repo,))
            threads_list.append(t)
            t.start()

        for t in threads_list:
            t.join()

        if len(err_dict) > 0:
            for k, v in err_dict.items():
                print("%s: %s" % (k, v))
            print("\n\nFailed :(")
            return 1
        print("All done :)")
        return 0

    @classmethod
    def init(cls):
        parser = OptionParser()
        parser.add_option("-v", "--verbose",
                          action="store_true",
                          dest="verbose",
                          default=False,
                          help="Run in verbose mode")
        (cls.options, args) = parser.parse_args()


if __name__ == "__main__":
    Syncer().run()
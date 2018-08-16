#!/usr/bin/python3
import threading
import subprocess
from builtins import classmethod
from pprint import pprint
import os
from optparse import OptionParser


REPOSITORIES = ['kernelight', 'usrlight', 'nvme-host']
WORKSPACE = os.environ.get('WORKSPACE_TOP', None)


class Syncer(object):
    err_dict = {}
    parser = None
    options = None
    rootfs_list = []

    @classmethod
    def _run_cmd(cls, cmd):
        print("*** Running: %s" % cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, encoding='utf8')
        out = p.communicate()
        if cls.options and cls.options.verbose:
            print("\nOUTPUT:\n")
            while p.poll() is None:
                print(p.stdout.readline())
        return p.returncode, out[0]

    @classmethod
    def _build_repo(cls, name):
        print("*** Building %s" % name)
        dir_path = os.path.join(WORKSPACE, name)
        assert os.path.exists(dir_path), "No such directory %s" % dir_path
        cmd = "cd %s && dockerize make" % dir_path
        if os.path.exists(os.path.join(dir_path, "Makefile.lb")):
            cmd += " -f Makefile.lb"
        rc, out = cls._run_cmd(cmd)
        if rc != 0:
            cls.err_dict[name] = out
        print("*** Done building %s" % name)

    @classmethod
    def _is_build_needed(cls):
        pass

    @classmethod
    def __build_repos(cls):
        threads_list = []
        for repo in REPOSITORIES:
            t = threading.Thread(target=cls._build_repo, args=(repo,))
            threads_list.append(t)
            t.start()

        for t in threads_list:
            t.join()

        if len(cls.err_dict) > 0:
            for k, v in cls.err_dict.items():
                print("%s: %s" % (k, v))
            print("\n\nFailed :(")
            return 1
        print("All done :)")
        return 0

    @classmethod
    def _build_rootfs(cls):
        if not cls.options.build_rootfs:
            return 0
        print("*** Building %s" % cls.options.build_rootfs)
        cmd = "cd %s/rootfs && dockerize make %s" % (WORKSPACE, cls.options.build_rootfs)
        rc, out = cls._run_cmd(cmd)
        if rc != 0:
            print(out)
            return 1
        print("*** Checking in new %s to Osmosis" % cls.options.build_rootfs)
        cmd = "cd %s/rootfs && dockerize make checkin_%s" % (WORKSPACE, cls.options.build_rootfs)
        rc, out = cls._run_cmd(cmd)
        if rc != 0:
            print(out)
            return 1
        return 0

    @classmethod
    def run(cls):
        cls._init()
        assert WORKSPACE, "Couldn't find workspace env variable"
        rc, out = cls._run_cmd("cd %s && repo sync" % WORKSPACE)
        assert rc == 0, "\nFailed to run 'repo sync'"
        rc = cls._build_rootfs()
        assert rc == 0, "\nFailed to build/check-in rootfs %s" % cls.options.build_rootfs
        return cls.__build_repos()

    @classmethod
    def __init_rootfs_list(cls):
        # grep rootfs_.*: %s/rootfs/lb.yaml | rev | cut -c 2- | rev ", os.Getenv("WORKSPACE_TOP")
        cmd = "grep rootfs_.*: %s/rootfs/lb.yaml | rev | cut -c 2- | rev " % WORKSPACE
        rc, out = cls._run_cmd(cmd)
        assert rc == 0, "Failed to fetch rootfs list"
        for rootfs_name in str(out).splitlines():
            cls.rootfs_list.append(rootfs_name.strip())

    @classmethod
    def _init(cls):
        parser = OptionParser()
        cls.__init_rootfs_list()
        parser.add_option("-v", "--verbose",
                          action="store_true",
                          dest="verbose",
                          default=False,
                          help="Run in verbose mode")
        parser.add_option("-f", "--force_build",
                          action="store_true",
                          dest="force_build",
                          default=False,
                          help="Build all repositories regardless their diff")
        parser.add_option("-b", "--build_rootfs",
                          type="choice",
                          choices=cls.rootfs_list,
                          action="store",
                          dest="build_rootfs",
                          default=None,
                          help="Build and checking given rootfs: %s" % ", ".join(cls.rootfs_list))
        (cls.options, args) = parser.parse_args()


if __name__ == "__main__":
    Syncer().run()
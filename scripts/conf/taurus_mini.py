import os
import socket
import subprocess as sp

import manager

from .miniapp import Miniapp

class Taurus_Mini(manager.Machine):
    def __init__(self, args):
        self.env = os.environ.copy()

        base =  self.env['HOME'] + "/interference-bench/miniapps/"

        self.modules_load = 'source {}/mini.env'.format(base)
        compile_command = self.modules_load + '; {}; make'
        tmpl = './{prog} {size_param}'
        self.group = \
            manager.BenchGroup(Miniapp, prog = ("CoMD-mpi",),
                               size_param = ("-i 2 -j 1 -k 1",),
                               size = (2,),
                               np = (2,),
                               wd = base + "CoMD/src-mpi/",
                               compile_command = compile_command.format('cd src-mpi'),
                               tmpl = tmpl)#  + \
            # manager.BenchGroup(Miniapp, prog = ("CoMD-ampi",),
            #                    size_param = ("-i 2 -j 2 -k 1",),
            #                    size = (4,),
            #                    np = (1, 2),
            #                    wd = base + "CoMD-1.1/bin/",
            #                    tmpl = tmpl) + \
            # manager.BenchGroup(Miniapp, prog = ("CoMD-ampi",),
            #                    size_param = ("-i 2 -j 2 -k 2",),
            #                    size = (8,),
            #                    np = (2, 4),
            #                    wd = base + "CoMD-1.1/bin/",
            #                    tmpl = tmpl)

        # self.group = \
        #             manager.BenchGroup(Miniapp, prog = ("lassen_mpi",),
        #                        size_param = ("default 2 2 2 200 200 200",),
        #                        size = (8,),
        #                        np = (1, 2),
        #                        wd = base + "Lassen-1.0/",
        #                        tmpl = tmpl)

        # self.group = \
        #     manager.BenchGroup(Miniapp, prog = ("lulesh2.0",),
        #                size_param = ("-i 300 -c 10 -b 3",),
        #                size = (8,),
        #                np = (2,),
        #                wd = base + "Lulesh-2.0/",
        #                tmpl = tmpl)

        self.mpiexec = 'mpirun_rsh'
        self.mpiexec_np = '-np'
        self.mpiexec_hostfile = '-hostfile {}'

        self.preload = 'LD_PRELOAD={}'

        self.lib = manager.Lib('mvapich',
                               compile_pre=self.modules_load,
                               compile_flags='')

        self.env['OMP_NUM_THREADS'] = '1'
        self.env['INTERFERENCE_LOCALID'] = 'MV2_COMM_WORLD_LOCAL_RANK'

        self.prefix = 'INTERFERENCE'

        self.schedulers = ("cfs",)
        self.affinities = ("2-3", "1,3")

        self.nodes = (1,)

        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = self.env['HOME'] + '/hostfiles'

        super().__init__(args)

    def get_nodelist(self):
        p = sp.run('scontrol show hostnames'.split(),
                       stdout = sp.PIPE)
        if p.returncode:
            raise Exception("Failed to get hosts")

        return list(p.stdout.decode('UTF-8').splitlines())

    def format_command(self, context):
        parameters = " ".join([self.mpiexec_hostfile.format(context.hostfile.path),
                               self.mpiexec_np, str(context.bench.np),
                               '-ssh',
                               '-export-all'])
        command = "{} ; taskset 0xFFFFFFFF {} {} {} ./../bin/{}"
        return command.format(self.modules_load, self.mpiexec, parameters,
                              self.preload.format(self.get_lib()), context.bench.name)

    def correct_guess():
        if 'taurusi' in socket.gethostname():
            return True
        return False

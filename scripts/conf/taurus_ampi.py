import os
import socket
import subprocess as sp

import manager

from .miniapp import Miniapp


class Taurus_AMPI(manager.Machine):
    def __init__(self, args):
        self.env = os.environ.copy()

        cpu_per_node = 24

        def np_func(nodes):
            return nodes * cpu_per_node

        def vp_func(nodes, oversub):
            return np_func(nodes) * oversub

        def comd_size_param(nodes):
            np = np_func(nodes)
            # Ensure that f has at least 3 groups
            domains = Miniapp.partition(np, 3)
            problem_size = '-x 200 -y 200 -z 200'
            problem_size = '-x 20 -y 20 -z 20'
            decomposition = '-i {} -j {} -k {} '.format(*domains)
            return decomposition + problem_size

        nodes = (1, 2, 4, 8)
        nodes = (8,)
        schedulers = ("cfs", )
        self.affinities = ("0-23",)

        base = self.env['HOME'] + "/interference-bench/"

        tmpl = './charmrun +p{np} ++mpiexec ++remote-shell {script} ' \
               './{prog} +vp{vp} {size_param} ++verbose'

        self.group = \
            manager.BenchGroup(Miniapp, prog=("CoMD-ampi",),
                               oversub=(1, 2, 4),
                               size=(1,),
                               vp=vp_func,
                               np=np_func,
                               schedulers=schedulers,
                               nodes=nodes,
                               size_param=comd_size_param,
                               wd=base + "CoMD-1.1/bin/",
                               tmpl=tmpl)

        def lassen_size_param(size, nodes, max_nodes):
            np = np_func(nodes)
            # Ensure that f has at least 3 groups
            domains = Miniapp.partition(np, 3)
            decomposition = '{} {} {}'.format(*domains)
            global_zones = ' {}'.format(cpu_per_node * max_nodes * size) * 3
            return "default {} {}".format(decomposition, global_zones)

        self.group = \
            manager.BenchGroup(Miniapp, prog=("lassen_mpi",),
                               oversub=(1, 2, 4),
                               size_param=lassen_size_param,
                               vp=vp_func,
                               size=(2,),
                               nodes=nodes,
                               np=np_func,
                               schedulers=schedulers,
                               max_nodes=max(nodes),
                               wd=base + "Lassen-1.0/",
                               tmpl=tmpl)

        def lulesh_np_func(nodes):
            return {1: 8, 2: 27, 4: 64,
                    8: 125, 16: 343, 32: 729, 64: 1331}[nodes]

        def lulesh_vp_func(nodes, oversub):
            return lulesh_np_func(nodes * oversub)

        self.group = \
            manager.BenchGroup(Miniapp, prog=("lulesh2.0",),
                               oversub=(1, 2, 4),
                               size=(1,),
                               size_param=("-i 300 -c 10 -b 3",),
                               vp=lulesh_vp_func,
                               np=lulesh_np_func,
                               schedulers=schedulers,
                               nodes=nodes,
                               wd=base + "Lulesh-2.0/",
                               tmpl=tmpl)

        charm_path = self.env['HOME'] + \
            '/ampi/charm/verbs-linux-x86_64-gfortran-gcc/'
        self.env['PATH'] = self.env['PATH'] + ":" + charm_path + "bin"

        self.lib = manager.Lib('charm', '-Dtest=ON -Dfortran=ON'
                               ' -DMPI_CC_COMPILER=ampicc'
                               ' -Dwrapper=OFF'
                               ' -DMPI_CXX_COMPILER=ampicxx'
                               ' -DMPI_CXX_INCLUDE_PATH={path}/include/'
                               ' -DMPI_CXX_LIBRARIES={path}/lib/'
                               ' -DMPI_C_LIBRARIES={path}/lib/'
                               ' -DMPI_C_INCLUDE_PATH='
                               '{path}/include/'.format(path=charm_path))

        self.prefix = 'INTERFERENCE'

        self.runs = (i for i in range(3))
        self.benchmarks = self.group.benchmarks

        self.nodelist = self.get_nodelist()
        self.hostfile_dir = self.env['HOME'] + '/hostfiles'

        super().__init__(args)

        old_ld = self.env['LD_LIBRARY_PATH'] + \
            ':' if 'LD_LIBRARY_PATH' in self.env else ''
        self.env['LD_LIBRARY_PATH'] = old_ld + self.get_lib_path()
        print(self.env['LD_LIBRARY_PATH'])

    def get_nodelist(self):
        p = sp.run('scontrol show hostnames'.split(),
                   stdout=sp.PIPE)
        if p.returncode:
            raise Exception("Failed to get hosts")

        return list(p.stdout.decode('UTF-8').splitlines())

    def format_command(self, context):
        command = " ".join(
            [context.bench.name.format(script=context.script.path)])
        print(command)
        return command

    def correct_guess():
        if 'taurusi' in socket.gethostname():
            return True
        return False

    def create_context(self, machine, cfg):
        return self.Context(self, cfg)

    class Context(manager.Context):
        def __enter__(self):
            self.script = self.create_script(
                self.machine.hostfile_dir, 'script')
            self.script.f.write("\n".join(
                ['#!/bin/bash -f',
                 'shift',
                 'exec srun -N {nodes} '
                 '-n $*'.format(nodes=self.bench.nodes)]) + '\n')

            return super().__enter__()

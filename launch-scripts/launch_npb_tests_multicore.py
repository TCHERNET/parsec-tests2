import os
import sys
from uuid import UUID

from gem5art.artifact import Artifact
from gem5art.run import gem5Run
from gem5art.tasks.tasks import run_gem5_instance

packer = Artifact.registerArtifact(
    command = '''wget https://releases.hashicorp.com/packer/1.4.3/packer_1.4.3_linux_amd64.zip;
    unzip packer_1.4.3_linux_amd64.zip;
    ''',
    typ = 'binary',
    name = 'packer',
    path =  'disk-image/packer',
    cwd = 'disk-image',
    documentation = 'Program to build disk images. Downloaded sometime in August from hashicorp.'
)

experiments_repo = Artifact.registerArtifact(
    command = 'git clone https://your-remote-add/npb-tests.git',
    typ = 'git repo',
    name = 'npb_tests',
    path =  './',
    cwd = '../',
    documentation = 'main repo to run npb multicore tests with gem5'
)

gem5_repo = Artifact.registerArtifact(
    command = '''
        git clone https://gem5.googlesource.com/public/gem5;
        cd gem5;
        git remote add darchr https://github.com/darchr/gem5;
        git fetch darchr;
        git cherry-pick 6450aaa7ca9e3040fb9eecf69c51a01884ac370c;
        git cherry-pick 3403665994b55f664f4edfc9074650aaa7ddcd2c;
    ''',
    typ = 'git repo',
    name = 'gem5',
    path =  'gem5/',
    cwd = './',
    documentation = 'cloned gem5 master branch from googlesource (Nov 18, 2019) and cherry-picked 2 commits from darchr/gem5'
)

m5_binary = Artifact.registerArtifact(
    command = 'make -f Makefile.x86',
    typ = 'binary',
    name = 'm5',
    path =  'gem5/util/m5/m5',
    cwd = 'gem5/util/m5',
    inputs = [gem5_repo,],
    documentation = 'm5 utility'
)

disk_image = Artifact.registerArtifact(
    command = './packer build npb/npb.json',
    typ = 'disk image',
    name = 'npb',
    cwd = 'disk-image',
    path = 'disk-image/npb/npb-image/npb',
    inputs = [packer, experiments_repo, m5_binary,],
    documentation = 'Ubuntu with m5 binary and NPB (with ROI annotations: darchr/npb-hooks/gem5art-npb-tutorial) installed.'
)

gem5_binary = Artifact.registerArtifact(
    command = 'scons build/X86/gem5.opt',
    typ = 'gem5 binary',
    name = 'gem5',
    cwd = 'gem5/',
    path =  'gem5/build/X86/gem5.opt',
    inputs = [gem5_repo,],
    documentation = 'gem5 binary based on googlesource (Nov 18, 2019) gem5 with cherry-picked commits from darchr/gem5'
)

linux_repo = Artifact.registerArtifact(
    command = '''git clone --branch v4.19.83 --depth 1 https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git;
    mv linux linux-stable''',
    typ = 'git repo',
    name = 'linux-stable',
    path =  'linux-stable/',
    cwd = './',
    documentation = 'linux kernel source code repo'
)

linux_binary = Artifact.registerArtifact(
    name = 'vmlinux-4.19.83',
    typ = 'kernel',
    path = 'linux-stable/vmlinux-4.19.83',
    cwd = 'linux-stable/',
    command = '''
    cp ../config.4.19.83 .config;
    make -j8;
    cp vmlinux vmlinux-4.19.83;
    ''',
    inputs = [experiments_repo, linux_repo,],
    documentation = "kernel binary for v4.19.83",
)


if __name__ == "__main__":
    num_cpus = ['1', '8', '16', '32', '64']
    benchmarks = ['is.x', 'ep.x', 'cg.x', 'mg.x','ft.x', 'bt.x', 'sp.x', 'lu.x']

    classes = ['A']
    cpus = ['kvm', 'timing']

for cpu in cpus:
    for num_cpu in num_cpus:
        for clas in classes:
            for bm in benchmarks:
                run = gem5Run.createFSRun(
                    'npb_multicore_tests',    
                    'gem5/build/X86/gem5.opt',
                    'configs-npb-tests-multicore/run_npb_multicore.py',
                    f'''results/run_npb_multicore/{bm}/{clas}/{cpu}/{num_cpu}''',
                    gem5_binary, gem5_repo, experiments_repo,
                    'linux-stable/vmlinux-4.19.83',
                    'disk-image/npb/npb-image/npb',
                    linux_binary, disk_image,
                    cpu, bm.replace('.x', f'.{clas}.x'), num_cpu,
                    timeout = 240*60*60 #240 hours
                    )
                run_gem5_instance.apply_async((run, '/fasthome/aakahlow/npb_tests/', ))

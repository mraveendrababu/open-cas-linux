#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from api.cas import casadm
from api.cas import ioclass_config
from api.cas.cache_config import CacheMode, CleaningPolicy
from storage_devices.disk import DiskType
from tests.conftest import base_prepare
from core.test_run import TestRun
from test_utils.size import Size, Unit

ioclass_config_path = "/tmp/opencas_ioclass.conf"
mountpoint = "/tmp/cas1-1"


def prepare():
    base_prepare()
    ioclass_config.remove_ioclass_config()
    cache_device = next(filter(
        lambda disk: disk.disk_type in [DiskType.optane, DiskType.nand],
        TestRun.dut.disks
    ))
    core_device = next(filter(
        lambda disk: disk.disk_type.value > cache_device.disk_type.value,
        TestRun.dut.disks
    ))

    cache_device.create_partitions([Size(500, Unit.MebiByte)])
    core_device.create_partitions([Size(1, Unit.GibiByte)])

    cache_device = cache_device.partitions[0]
    core_device = core_device.partitions[0]

    TestRun.LOGGER.info(f"Starting cache")
    cache = casadm.start_cache(cache_device, cache_mode=CacheMode.WB, force=True)
    TestRun.LOGGER.info(f"Setting cleaning policy to NOP")
    casadm.set_param_cleaning(cache_id=cache.cache_id, policy=CleaningPolicy.nop)
    TestRun.LOGGER.info(f"Adding core device")
    core = casadm.add_core(cache, core_dev=core_device)

    ioclass_config.create_ioclass_config(
        add_default_rule=False, ioclass_config_path=ioclass_config_path
    )
    # To make test more precise all workload except of tested ioclass should be
    # put in pass-through mode
    ioclass_config.add_ioclass(
        ioclass_id=0,
        eviction_priority=22,
        allocation=False,
        rule="unclassified",
        ioclass_config_path=ioclass_config_path,
    )

    output = TestRun.executor.run(f"mkdir -p {mountpoint}")
    if output.exit_code != 0:
        raise Exception(f"Failed to create mountpoint")

    return cache, core

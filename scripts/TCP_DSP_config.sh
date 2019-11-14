#!/usr/bin/env bash
# shellcheck disable=SC2028
echo "-----<<|  Remote DPS config service  |>>----- \nCTRL-C to end."

./../hardware/sigma-tcp-adau1701/sigma_tcp i2c /dev/i2c-1 0x34
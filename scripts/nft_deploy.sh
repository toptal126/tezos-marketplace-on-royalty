#!/bin/bash

_PATH="~/Documents/tezos-marketplace-smartpy"

rm compilation -r & ~/smartpy-cli/SmartPy.sh compile ./contracts/LimitedNFT.py compilation

~/smartpy-cli/SmartPy.sh originate-contract \
    --code ~/Documents/tezos-marketplace-smartpy/compilation/NFTWithArtists_Compiled/step_000_cont_0_contract.tz \
    --storage ~/Documents/tezos-marketplace-smartpy/compilation/NFTWithArtists_Compiled/step_000_cont_0_storage.tz \
    --rpc https://rpc.tzkt.io/ghostnet \
    --private-key $1
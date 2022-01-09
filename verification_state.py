#!/usr/bin/env python3

###########################################################################
# Copyright 2017 ZT Prentner IT GmbH (www.ztp.at)
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
###########################################################################

from builtins import int
from builtins import range

from six import string_types

import copy
import json
import sys

import gettext
gettext.install('rktool', './lang', True)

from librksv import depparser
from librksv import utils
from librksv.receipt import Receipt
from librksv.verification_state import (CashRegisterState, ClusterState,
        DEFAULT_USED_RECEIPT_IDS_BACKEND)

def printStateField(name, value):
    print(u'{: >25}: {}'.format(name, value))

def printCashRegisterState(state):
    printStateField(_('Start Receipt'), state.startReceiptJWS)
    printStateField(_('Last Receipt'), state.lastReceiptJWS)
    printStateField(_('Last Turnover Counter'), state.lastTurnoverCounter)
    printStateField(_('Need Restore Receipt'), state.needRestoreReceipt)

def printClusterState(state):
    for i in range(len(state.cashRegisters)):
        print(_('Cash Register {}:').format(i))
        printCashRegisterState(state.cashRegisters[i])
        print('')
    # TODO: add a proper print function per type
    printStateField(_('Used Receipt IDs Backend'),
            state.usedReceiptIds.__class__._backendType)

INPUT_FORMATS = {
        'jws': lambda s: Receipt.fromJWSString(s),
        'qr': lambda s: Receipt.fromBasicCode(s),
        'ocr': lambda s: Receipt.fromOCRCode(s),
        'url': lambda s: Receipt.fromBasicCode(getBasicCodeFromURL(
            s)),
        'csv': lambda s: Receipt.fromCSV(s)
        }

def usage():
    print("Usage: ./verification_state.py <state> create")
    print("       ./verification_state.py <state> show")
    print("       ./verification_state.py <state> addCashRegister")
    print("       ./verification_state.py <state> resetCashRegister <n>")
    print("       ./verification_state.py <state> deleteCashRegister <n>")
    print("       ./verification_state.py <state> copyCashRegister <n-Target> <source state file> <n-Source>")
    print("       ./verification_state.py <state> updateCashRegister <n-Target> <dep export file> [<base64 AES key file>]")
    print("       ./verification_state.py <state> setLastReceiptJWS <n> <receipt in JWS format>")
    print("       ./verification_state.py <state> setLastTurnoverCounter <n> <counter in cents>")
    print("       ./verification_state.py <state> setChainNextTo <n> <chaining value>")
    print("       ./verification_state.py <state> toggleNeedRestoreReceipt <n>")
    print("       ./verification_state.py <state> setStartReceiptJWS <n> <receipt in JWS format>")
    print("       ./verification_state.py <state> readUsedReceiptIds <file with one receipt ID per line>")
    print("       ./verification_state.py <state> fromArbitraryReceipt <in format> <receipt in in format> [<base64 AES key file>]")
    print("       ./verification_state.py <state> fromArbitraryStartReceipt <in format> <receipt in in format>")
    sys.exit(0)

if __name__ == "__main__":
    def load_state(filename):
        with open(filename, 'r') as f:
            stateJson = utils.readJsonStream(f)
            return ClusterState.readStateFromJson(stateJson)

    def arg_str_or_none(arg):
        if arg == 'None':
            return None
        return arg

    def arg_list_from_file_or_empty(arg):
        if arg == 'None':
            return list()
        with open(arg, 'r') as f:
            return [l.strip() for l in f.readlines()]

    if len(sys.argv) < 3:
        usage()

    recIdsBackend = DEFAULT_USED_RECEIPT_IDS_BACKEND
    filename = sys.argv[1]
    state = None

    if sys.argv[2] == 'create':
        if len(sys.argv) != 3:
            usage()

        state = ClusterState(recIdsBackend)

    elif sys.argv[2] == 'show':
        if len(sys.argv) != 3:
            usage()

        state = load_state(filename)

        printClusterState(state)

    elif sys.argv[2] == 'addCashRegister':
        if len(sys.argv) != 3:
            usage()

        state = load_state(filename)
        state.addNewCashRegister()

    elif sys.argv[2] == 'resetCashRegister':
        if len(sys.argv) != 4:
            usage()

        state = load_state(filename)
        state.updateCashRegisterInfo(int(sys.argv[3]), CashRegisterState(),
                recIdsBackend())

    elif sys.argv[2] == 'deleteCashRegister':
        if len(sys.argv) != 4:
            usage()

        state = load_state(filename)
        del state.cashRegisters[int(sys.argv[3])]

    elif sys.argv[2] == 'setLastReceiptJWS':
        if len(sys.argv) != 5:
            usage()

        state = load_state(filename)
        state.cashRegisters[int(
            sys.argv[3])].lastReceiptJWS = arg_str_or_none(sys.argv[4])

    elif sys.argv[2] == 'setLastTurnoverCounter':
        if len(sys.argv) != 5:
            usage()

        state = load_state(filename)
        state.cashRegisters[int(
            sys.argv[3])].lastTurnoverCounter = int(sys.argv[4])

    elif sys.argv[2] == 'setChainNextTo':
        if len(sys.argv) != 5:
            usage()

        state = load_state(filename)
        state.cashRegisters[int(
            sys.argv[3])].chainNextTo = arg_str_or_none(sys.argv[4])

    elif sys.argv[2] == 'toggleNeedRestoreReceipt':
        if len(sys.argv) != 4:
            usage()

        state = load_state(filename)
        state.cashRegisters[int(
            sys.argv[3])].needRestoreReceipt = not state.cashRegisters[int(
                sys.argv[3])].needRestoreReceipt

    elif sys.argv[2] == 'setStartReceiptJWS':
        if len(sys.argv) != 5:
            usage()

        state = load_state(filename)
        state.cashRegisters[int(
            sys.argv[3])].startReceiptJWS = arg_str_or_none(sys.argv[4])

    elif sys.argv[2] == 'readUsedReceiptIds':
        if len(sys.argv) != 4:
            usage()

        state = load_state(filename)
        state.usedReceiptIds = recIdsBackend()
        for rId in arg_list_from_file_or_empty(sys.argv[3]):
            state.usedReceiptIds.add(rId)

    elif sys.argv[2] == 'copyCashRegister':
        if len(sys.argv) != 6:
            usage()

        state = load_state(filename)
        srcState = load_state(sys.argv[4])

        state.cashRegisters[int(
            sys.argv[3])] = srcState.cashRegisters[int(sys.argv[5])]

    elif sys.argv[2] == 'updateCashRegister':
        if len(sys.argv) != 5 and len(sys.argv) != 6:
            usage()

        key = None
        if len(sys.argv) == 6:
            with open(sys.argv[5]) as f:
                key = utils.loadB64Key(f.read().encode("utf-8"))

        state = load_state(filename)

        with open(sys.argv[4]) as f:
            parser = depparser.CertlessStreamDEPParser(f)

            for chunk in parser.parse(utils.depParserChunkSize()):
                for recs, cert, chain in chunk:
                    state.cashRegisters[int(sys.argv[3])].updateFromDEPGroup(recs, key)

                    recs = None
                chunk = None

    elif sys.argv[2] == 'fromArbitraryReceipt':
        if len(sys.argv) != 5 and len(sys.argv) != 6:
            usage()

        if sys.argv[3] not in INPUT_FORMATS:
            print(_("Input format must be one of %s.") % INPUT_FORMATS.keys())
            sys.exit(0)

        key = None
        if len(sys.argv) == 6:
            with open(sys.argv[5]) as f:
                key = utils.loadB64Key(f.read().encode("utf-8"))

        r, p = INPUT_FORMATS[sys.argv[3]](sys.argv[4].strip())

        state = ClusterState.fromArbitraryReceipt(r, p, key, recIdsBackend)

    elif sys.argv[2] == 'fromArbitraryStartReceipt':
        if len(sys.argv) != 5:
            usage()

        if sys.argv[3] not in INPUT_FORMATS:
            print(_("Input format must be one of %s.") % INPUT_FORMATS.keys())
            sys.exit(0)

        r, p = INPUT_FORMATS[sys.argv[3]](sys.argv[4].strip())

        state = ClusterState.fromArbitraryStartReceipt(r, recIdsBackend)

    else:
        usage()

    stateJson = state.writeStateToJson()
    with open(filename, 'w') as f:
        json.dump(stateJson, f, sort_keys=False, indent=2)

import smartpy as sp

FA2 = sp.io.import_script_from_url("https://smartpy.io/templates/fa2_lib.py")
Utils = sp.io.import_script_from_url(
    "https://raw.githubusercontent.com/RomarQ/tezos-sc-utils/main/smartpy/utils.py")


class MultiAdmin:
    """(Mixin) Provide the basics for having an administrator in the contract.

    Adds an `administrator` attribute in the storage record. Provides a
    `set_administrator` entrypoint. Provides a `is_administrator` meta-
    programming function.
    """

    def __init__(self, admin, administrators=[]):
        self.update_initial_storage(admin=admin, administrators=administrators)

    def is_administrator(self, sender):
        return self.data.admin == sender
        # return sp.fst(self.data.administrators[0]) == sender
        # result = sp.local('result', False)
        # with sp.for_("administrator", self.data.administrators) as administrator:
        #     with sp.if_(sp.fst(administrator) == sender):
        #         result.value = True
        # return result.value

    def is_administrators(self, sender):
        result = sp.local('result', False)
        with sp.for_("administrator", self.data.administrators) as administrator:
            with sp.if_(sp.fst(administrator) == sender):
                result.value = True
        return result.value

    @sp.entry_point
    def set_administrators(self, params):
        sp.set_type(
            params,
            sp.TList(
                sp.TPair(
                    sp.TAddress,
                    sp.TNat
                )
            ),
        )
        """(Admin only) Set the contract administrator."""
        sp.verify(self.is_administrator(sp.sender), message="FA2_NOT_ADMIN")
        self.data.administrators = params


class VaultContract(MultiAdmin, sp.Contract):
    def __init__(self, admin, administrators, **kwargs):
        MultiAdmin.__init__(self, admin, administrators)

    @sp.entry_point
    def default(self):
        pass

    @sp.entry_point
    def distribute_mutez(self):
        """(Admin only) Transfer `amount` mutez to `destination`."""
        sp.verify(self.is_administrators(sp.sender), message="FA2_NOT_ADMIN")
        _current_balance = sp.balance

        with sp.for_("administrator", self.data.administrators) as administrator:
            sp.send(sp.fst(administrator),
                    sp.split_tokens(_current_balance, sp.snd(administrator), 10000))

    @sp.offchain_view()
    def some_computation(self, sender):
        sp.result(self.is_administrator(sender))


@ sp.add_test(name="NFT with admin and mint")
def test():
    sc = sp.test_scenario()
    vault_contract = VaultContract(
        admin=sp.address("tz1U629U2nmfaDT3wcDjJbDVdGd8qaRmAsuB"),
        administrators=sp.list([
            # alex
            sp.pair(sp.address("tz1U629U2nmfaDT3wcDjJbDVdGd8qaRmAsuB"), 500),
            # ethan
            sp.pair(sp.address("tz1U9M4zduAFdWwob8YxiZSr5T6t77ds2FbG"), 2500),
            sp.pair(sp.address("tz1aSjTFeHjd5zhrbE1JEvrEnkA1TiKmPwwF"), 750),
            sp.pair(sp.address("tz1iSBP9FM4mYmUjDGhFzRAcmZtyrL9h87rL"), 500),
            sp.pair(sp.address("tz1SFEz5qNpEs2p4CyJ779BD1L1UAkXZo7Ji"), 500),
            sp.pair(sp.address("tz1YSXSuPRB397bBrTCLF12gGLeDbuq9LkqW"), 500),
            sp.pair(sp.address("tz1V21h74sKjQzvnpXhp9hmG58cY4ZgYNwGQ"), 500),
            sp.pair(sp.address("tz1ezqViSWyHHK9zKoEUzgSY1LWcqqCpbvzf"), 500),
            # investors
            sp.pair(sp.address("tz1hF85xpacR6nyJWcHJTp1upfmVoUBYAPF4"), 850),
            sp.pair(sp.address("tz1XaAGZAc9aZL8rBfMtpfLgojGPkkVJsMye"), 800),
            sp.pair(sp.address("tz1WuQ1ZgnSn2i2KUEVKHB2P44AW1JzhSKyM"), 800),

            #  devs
            sp.pair(sp.address("tz1MnoSe4HMAzfoyiPGkrAL6a3WzBhRQRba9"), 800),
            sp.pair(sp.address("tz1guAEwUfG6LkKoeETyhMebE2izdCC1RKpE"), 500)
        ]))
    sc += vault_contract
    vault_contract.default().run(amount=sp.mutez(60000))
    vault_contract.distribute_mutez().run(
        sender=sp.address("tz1U9M4zduAFdWwob8YxiZSr5T6t77ds2FbG"))

    vault_contract.set_administrators([
        # alex
        sp.pair(sp.address("tz1U629U2nmfaDT3wcDjJbDVdGd8qaRmAsuB"), 500),
        # ethan
        sp.pair(sp.address("tz1U9M4zduAFdWwob8YxiZSr5T6t77ds2FbG"), 2500),
        sp.pair(sp.address("tz1aSjTFeHjd5zhrbE1JEvrEnkA1TiKmPwwF"), 750)]).run(sender=sp.address("tz1U629U2nmfaDT3wcDjJbDVdGd8qaRmAsuB"))


# A a compilation target (produces compiled code)
sp.add_compilation_target("Vault_Compiled", VaultContract(
    admin=sp.address("tz1U629U2nmfaDT3wcDjJbDVdGd8qaRmAsuB"),
    administrators=sp.list([
        # alex
        sp.pair(sp.address("tz1U629U2nmfaDT3wcDjJbDVdGd8qaRmAsuB"), 500),
        # ethan
        sp.pair(sp.address("tz1U9M4zduAFdWwob8YxiZSr5T6t77ds2FbG"), 2500),
        sp.pair(sp.address("tz1aSjTFeHjd5zhrbE1JEvrEnkA1TiKmPwwF"), 750),
        sp.pair(sp.address("tz1iSBP9FM4mYmUjDGhFzRAcmZtyrL9h87rL"), 500),
        sp.pair(sp.address("tz1SFEz5qNpEs2p4CyJ779BD1L1UAkXZo7Ji"), 500),
        sp.pair(sp.address("tz1YSXSuPRB397bBrTCLF12gGLeDbuq9LkqW"), 500),
        sp.pair(sp.address("tz1V21h74sKjQzvnpXhp9hmG58cY4ZgYNwGQ"), 500),
        sp.pair(sp.address("tz1ezqViSWyHHK9zKoEUzgSY1LWcqqCpbvzf"), 500),
        # investors
        sp.pair(sp.address("tz1hF85xpacR6nyJWcHJTp1upfmVoUBYAPF4"), 850),
        sp.pair(sp.address("tz1XaAGZAc9aZL8rBfMtpfLgojGPkkVJsMye"), 800),
        sp.pair(sp.address("tz1WuQ1ZgnSn2i2KUEVKHB2P44AW1JzhSKyM"), 800),

        #  devs
        sp.pair(sp.address("tz1MnoSe4HMAzfoyiPGkrAL6a3WzBhRQRba9"), 800),
        sp.pair(sp.address("tz1guAEwUfG6LkKoeETyhMebE2izdCC1RKpE"), 500)
    ])
))


# Wallet Allocation of 2.5% fees:

# 25% Business Development Costs
# tz1U9M4zduAFdWwob8YxiZSr5T6t77ds2FbG (0.00625)
# ——————————————————
# Ethan Herlihy (Founder)
# 37.5% Total:
# 7.5%: (0.001875) tz1aSjTFeHjd5zhrbE1JEvrEnkA1TiKmPwwF

# 5%: (0.00125) tz1iSBP9FM4mYmUjDGhFzRAcmZtyrL9h87rL

# 5%: (0.00125) tz1SFEz5qNpEs2p4CyJ779BD1L1UAkXZo7Ji

# 5%: (0.00125) tz1YSXSuPRB397bBrTCLF12gGLeDbuq9LkqW

# 5%:(0.00125) tz1V21h74sKjQzvnpXhp9hmG58cY4ZgYNwGQ

# 5%:
# tz1ezqViSWyHHK9zKoEUzgSY1LWcqqCpbvzf

# ——————————————————
# Investors:
# 8.5% David Anyakora
# (0.002125) tz1hF85xpacR6nyJWcHJTp1upfmVoUBYAPF4

# 8% (0.002) Alex D. tz1XaAGZAc9aZL8rBfMtpfLgojGPkkVJsMye

# 8% (0.002) Matt H.
# tz1WuQ1ZgnSn2i2KUEVKHB2P44AW1JzhSKyM
# ——————————————————
# Development:
# 5% (0.00125) Oleksandr Z. tz1U629U2nmfaDT3wcDjJbDVdGd8qaRmAsuB

# 8% (0.002) “m00n” Chase C.
# tz1MnoSe4HMAzfoyiPGkrAL6a3WzBhRQRba9

# 5% Aki J. (0.00125)

# tz1guAEwUfG6LkKoeETyhMebE2izdCC1RKpE

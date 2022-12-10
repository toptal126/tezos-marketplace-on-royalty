import smartpy as sp

LimitedNFT = sp.io.import_script_from_url(
    "file:///home/alex/Documents/tezos-marketplace-smartpy/contracts/LimitedNFT.py")

FA2 = sp.io.import_script_from_url("https://smartpy.io/templates/fa2_lib.py")
Utils = sp.io.import_script_from_url(
    "https://raw.githubusercontent.com/RomarQ/tezos-sc-utils/main/smartpy/utils.py")


T_BALANCE_OF_REQUEST = sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(
    ("owner", "token_id")
)

GHOSTNET_ADDRESSES = {
    "ArtistsNFT": sp.address("KT1KVkLkevQhW126HeUiLiNiWnK9E5Gu6zL3"),
    "Vault": sp.address("KT1NCMAbF1TNBnKKUQFgjPpjA7pXK27Dc2Gq")
}

ADDRESS_SET = GHOSTNET_ADDRESSES


T_ORDER_ITEM = sp.TRecord(
    order_id=sp.TNat,
    owner=sp.TAddress,
    price=sp.TMutez,
)


class NftOwnerCheck:
    def __init__(self, artistnft_address):
        self.update_initial_storage(
            artistnft_address=artistnft_address,
            temp_balances=sp.list(l=[],
                                  t=sp.TRecord(
                request=T_BALANCE_OF_REQUEST,
                balance=sp.TNat,
            )),
            temp_token_id=0,
            temp_offer_amount=sp.mutez(0),
        )

    @sp.entry_point
    def set_balance_callback(self, balances):
        sp.verify(sp.sender == self.data.artistnft_address,
                  "NftOwnerCheck: Not authorised")

        with sp.for_("temp_balance", balances) as temp_balance:
            sp.verify(temp_balance.balance > 0, "NftOwnerCheck: Invalid Owner")

    def is_valid_owner(self, owner, token_id):
        contract = sp.contract(
            sp.TRecord(
                requests=sp.TList(
                    sp.TRecord(
                        owner=sp.TAddress,
                        token_id=sp.TNat
                    ).layout(("owner", "token_id"))
                ),
                callback=sp.TContract(
                    sp.TList(
                        sp.TRecord(
                            request=sp.TRecord(
                                owner=sp.TAddress,
                                token_id=sp.TNat
                            ).layout(("owner", "token_id")),
                            balance=sp.TNat
                        ).layout(("request", "balance"))
                    )
                )
            ).layout(("requests", "callback")),
            self.data.artistnft_address,
            entry_point="balance_of").open_some()
        requests = sp.list([sp.record(owner=owner, token_id=token_id)])
        params = sp.record(callback=sp.self_entry_point(
            entry_point="set_balance_callback"), requests=requests)
        sp.transfer(params, sp.mutez(0), contract)

    @sp.entry_point
    def set_minter_callback(self, result):
        sp.set_type(result, sp.TPair(sp.TAddress, sp.TNat))

        platform_mutez = sp.local(
            'platform_mutez', sp.split_tokens(self.data.temp_offer_amount, self.data.platform_fee,  10000))

        royalty_mutez = sp.local(
            'royalty_mutez', sp.split_tokens(self.data.temp_offer_amount, sp.snd(result),  10000))
        sp.send(sp.fst(result), royalty_mutez.value)
        sp.send(self.data.orders_map[self.data.temp_token_id].owner,
                self.data.temp_offer_amount - platform_mutez.value - royalty_mutez.value)

        self.data.temp_offer_amount = sp.mutez(0)
        self.data.temp_token_id = 0
        del self.data.orders_map[self.data.temp_token_id]

    def get_minter_of(self, token_id):
        contract = sp.contract(
            sp.TRecord(
                token_id=sp.TNat,
                callback=sp.TContract(sp.TPair(sp.TAddress, sp.TNat))
            ).layout(("token_id", "callback")),
            self.data.artistnft_address,
            entry_point="minter_of").open_some()

        params = sp.record(callback=sp.self_entry_point(
            entry_point="set_minter_callback"), token_id=token_id)

        sp.transfer(params, sp.mutez(0), contract)

    def transfer_domain_from_to(self, token_id, from_, to_):
        contract = sp.contract(
            t=sp.TList(sp.TRecord(from_=sp.TAddress, txs=sp.TList(sp.TRecord(
                to_=sp.TAddress, token_id=sp.TNat, amount=sp.TNat).layout(("to_", ("token_id", "amount")))))),
            address=self.data.artistnft_address,
            entry_point="transfer").open_some()
        sp.transfer(
            arg=sp.list([sp.record(
                from_=from_,
                txs=sp.list([sp.record(
                    to_=to_,
                    token_id=token_id,
                    amount=1)]))]),
            amount=sp.mutez(0),
            destination=contract)


class OrderStorage(sp.Contract):
    def __init__(self, vault_contract):
        self.update_initial_storage(
            next_order_id=0,
            platform_fee=250,
            vault_contract=vault_contract,
            orders_map=sp.big_map(
                {}, tkey=sp.TNat, tvalue=T_ORDER_ITEM),
        )

    def create_order(self, token_id, owner, default_amount):
        self.data.orders_map[token_id] = sp.record(
            order_id=self.data.next_order_id,
            owner=owner,
            price=default_amount,
        )

        self.data.next_order_id += 1

    def buy_for_sale(self, token_id, offer_amount):
        sp.verify(offer_amount >=
                  self.data.orders_map[token_id].price, "ResourceStorage: Must be greater than listing price")
        platform_mutez = sp.local(
            'platform_mutez', sp.split_tokens(offer_amount, self.data.platform_fee,  10000))

        self.data.temp_token_id = token_id
        self.data.temp_offer_amount = offer_amount
        self.get_minter_of(token_id)

        sp.send(self.data.vault_contract, platform_mutez.value)

    def is_active_order(self, token_id):
        sp.verify(self.data.orders_map.contains(token_id),
                  "No order for provided token_id")


class MarketPlace(FA2.Admin, NftOwnerCheck, OrderStorage):
    def __init__(self, admin, artistnft_address, vault_contract, **kwargs):
        FA2.Admin.__init__(self, admin)
        OrderStorage.__init__(self, vault_contract)
        NftOwnerCheck.__init__(self, artistnft_address)

    @ sp.entry_point
    def list_for_sale(self, token_id, default_amount):
        sp.set_type(token_id, sp.TNat)
        sp.set_type(default_amount, sp.TMutez)
        sp.verify(sp.amount == sp.mutez(0), "Amount is not Zero")
        self.is_valid_owner(sp.sender, token_id)
        self.create_order(token_id, sp.sender, default_amount)

    @ sp.entry_point
    def cancel_for_sale(self, token_id):
        sp.verify(sp.amount == sp.mutez(0), "Amount is not Zero")
        self.is_valid_owner(sp.sender, token_id)
        self.is_active_order(token_id)
        del self.data.orders_map[token_id]

    @ sp.entry_point
    def buy(self, token_id):
        self.is_active_order(token_id)
        self.buy_for_sale(token_id, sp.amount)
        self.transfer_domain_from_to(
            token_id, self.data.orders_map[token_id].owner, sp.sender)


admin = sp.test_account("admin")

artist1 = sp.test_account("artist1")
artist2 = sp.test_account("artist2")

user1 = sp.test_account("user1")
user2 = sp.test_account("user2")


@ sp.add_test(name="Game Gov with Resource manager")
def test():
    sc = sp.test_scenario()

    nft_contract = LimitedNFT.NFTWithArtists(
        admin=admin.address,
        artists=sp.list([
            sp.pair(artist1.address, 5),
            sp.pair(artist2.address, 10)
        ]),
        metadata=sp.utils.metadata_of_url(
            "ipfs://bafkreigb6nsuvwc7vzx6oqzoaeaxno6liyr5rigbheg2ol7ndac75kawoe"
        ),
        token_metadata=[],
    )
    sc += nft_contract

    marketplace_contract = MarketPlace(
        admin=sp.address("tz1i66XefcqsNVSGa2iFsWb8qxokm3neVpFR"),
        artistnft_address=nft_contract.address,
        vault_contract=ADDRESS_SET['Vault'],
    )
    sc += marketplace_contract

    nft_contract.mint([
        sp.record(to_=artist1.address,
                  metadata={
                      "": Utils.Bytes.of_string("ipfs://QmWoCRq4iXnUwzMF2JUUxSbXsTSiuitxvWiYQ27XXusfNu/0.json")
                  },
                  royalty=10)
    ]).run(
        sender=artist1
    )

    update_operator_variant = sp.variant("add_operator", sp.record(
        owner=artist1.address, operator=marketplace_contract.address, token_id=0))

    nft_contract.update_operators([update_operator_variant]).run(
        sender=artist1
    )

    marketplace_contract.list_for_sale(sp.record(token_id=0, default_amount=sp.mutez(10))).run(
        sender=artist1
    )

    marketplace_contract.buy(0).run(
        sender=user1,
        amount=sp.mutez(10000000)
    )


# A a compilation target (produces compiled code)
sp.add_compilation_target("MarketPlace_Compiled", MarketPlace(
    admin=sp.address("tz1i66XefcqsNVSGa2iFsWb8qxokm3neVpFR"),
    artistnft_address=ADDRESS_SET['ArtistsNFT'],
    vault_contract=ADDRESS_SET['Vault'],
))


'''
    Only owner can list domain(token_id) for sale
    If MarketPlace contract is set as operator
'''

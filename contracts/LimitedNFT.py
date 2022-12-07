import smartpy as sp

# FA2 = sp.io.import_script_from_url("https://smartpy.io/templates/fa2_lib.py")

FA2 = sp.io.import_script_from_url(
    "file:///home/alex/Documents/tezos-marketplace-smartpy/fa2_lib.py")

Utils = sp.io.import_script_from_url(
    "https://raw.githubusercontent.com/RomarQ/tezos-sc-utils/main/smartpy/utils.py")


def string_of_nat(params):
    c = sp.map({x: str(x) for x in range(0, 10)})
    x = sp.local('x', params)
    res = sp.local('res', [])
    with sp.if_(x.value == 0):
        res.value.push('0')
    with sp.while_(0 < x.value):
        res.value.push(c[x.value % 10])
        x.value //= 10
    return sp.concat(res.value)


t_minter_of_params = sp.TRecord(
    callback=sp.TContract(sp.TPair(sp.TAddress, sp.TNat)),
    token_id=sp.TNat
).layout(("token_id", "callback"))


class ArtistStorage:
    """(Mixin) Provide the basics for having multiple minters in the contract.

    Adds an `artist` attribute in the storage record. Provides a
    `set_artist` entrypoint. Provides a `is_artist` meta-
    programming function.
    """

    def __init__(self, artists=[]):
        self.update_initial_storage(artists=artists, minters=sp.big_map(
            l={}, tkey=sp.TNat, tvalue=sp.TAddress))

    def is_artist(self, sender):
        result = sp.local('result', False)
        with sp.for_("artist", self.data.artists) as artist:
            with sp.if_(sp.fst(artist) == sender):
                result.value = True
        return result.value

    @sp.entry_point
    def set_artists(self, params):
        sp.set_type(
            params,
            sp.TList(
                sp.TPair(
                    sp.TAddress,
                    sp.TNat
                )
            ),
        )
        """(Admin only) Set the contract artist."""
        sp.verify(self.is_administrator(sp.sender), "FA2_NOT_ADMIN")
        self.data.artists = params


class ArtistMintNFT(sp.Contract):
    """(Mixin) Non-standard `mint` entrypoint for FA2Nft with incrementing id.

    Requires the `Admin` mixin.
    """

    def __init__(self, token_royalties={}):
        self.update_initial_storage(token_royalties=sp.big_map(token_royalties, tkey=sp.TNat, tvalue=sp.TNat))

    @sp.entry_point
    def mint(self, batch):
        """Artist can mint new or existing tokens."""
        sp.set_type(
            batch,
            sp.TList(
                sp.TRecord(
                    to_=sp.TAddress,
                    metadata=sp.TMap(sp.TString, sp.TBytes),
                    royalty=sp.TNat
                ).layout(("royalty", ("to_", "metadata")))
            ),
        )
        sp.verify(self.is_artist(sp.sender), "ArtistsStorage: Not a Artist")

        with sp.for_("action", batch) as action:
            token_id = sp.compute(self.data.last_token_id)
            metadata = sp.record(token_id=token_id, token_info=action.metadata)
            self.data.token_metadata[token_id] = metadata
            self.data.ledger[token_id] = action.to_
            self.data.minters[token_id] = sp.sender

            sp.verify(action.royalty <= 15, "Invalid Royalty")
            self.data.token_royalties[token_id] = action.royalty

            self.data.last_token_id += 1


class NFTWithArtists(FA2.Admin, FA2.WithdrawMutez, ArtistMintNFT, FA2.Fa2Nft, ArtistStorage):
    def __init__(self, admin, artists, metadata, token_metadata):
        FA2.Fa2Nft.__init__(self, metadata, token_metadata)
        FA2.Admin.__init__(self, admin)
        ArtistStorage.__init__(self, artists)
        ArtistMintNFT.__init__(self, {})

    @sp.entry_point
    def minter_of(self, params):
        sp.set_type(params, t_minter_of_params)

        _artist = sp.local('_artist', sp.pair(self.data.administrator, 0))
        with sp.for_("artist", self.data.artists) as artist:
            with sp.if_(sp.fst(artist) == self.data.minters[params.token_id]):
                _artist.value = artist

        sp.transfer(_artist.value, sp.mutez(0), params.callback)


tok0_md = sp.map(l={
    "": sp.utils.bytes_of_string(
        "ipfs://QmTq1FXht8jFc9CaW2j2hJ3bMjLqgAJhr3bxjcJ723TaHT"
    ),
})


artist1 = sp.address("tz1Zn3WK57gjcsk6WH8MD6jf4VEqXuRfgPFM")
artist2 = sp.address("tz1U629U2nmfaDT3wcDjJbDVdGd8qaRmAsuB")


@ sp.add_test(name="NFT with admin and artists")
def test():
    sc = sp.test_scenario()


# A a compilation target (produces compiled code)
sp.add_compilation_target("NFTWithArtists_Compiled", NFTWithArtists(
    admin=sp.address("tz1i66XefcqsNVSGa2iFsWb8qxokm3neVpFR"),
    artists=sp.list([
        sp.pair(artist1, 500),
        sp.pair(artist2, 1000)
    ]),
    metadata=sp.utils.metadata_of_url(
        "ipfs://bafkreigb6nsuvwc7vzx6oqzoaeaxno6liyr5rigbheg2ol7ndac75kawoe"
    ),
    token_metadata=[],
))

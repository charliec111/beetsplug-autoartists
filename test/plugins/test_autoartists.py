import unittest
import pytest
from beets import config
from beets.test import _common
from beets.test.helper import BeetsTestCase
from beetsplug import autoartists


class AutoArtistsPluginTest(BeetsTestCase):
    def setUp(self):
        super().setUp()
        self.plugin = autoartists.AutoArtistsPlugin()

    def _setup_config(self, single_artists=["Earth, Wind & Fire", "A and B"]):
        print(f"single artists: {single_artists}")
        self.config["autoartists"]["single_artists"] = single_artists
        self.plugin.__init__()

    def test_whitelist(self):
        self.setUp()
        artist_whitelist = ["Earth, Wind & Fire"]
        self._setup_config(single_artists=artist_whitelist)
        test_result = self.plugin.get_artists("Jim Croce", "a song title")
        assert test_result == ["Jim Croce"]

        assert (
            len(self.plugin.get_artists("Jim Croce and Another artist", "a song title"))
            == 2
        )
        assert (
            len(self.plugin.get_artists("Jim Croce & Another artist", "a song title"))
            == 2
        )
        assert len(self.plugin.get_artists(artist_whitelist[0], "September")) == 1
        assert len(self.plugin.get_artists(artist_whitelist[0], "September")) == 1
        assert (
            len(
                self.plugin.get_artists(
                    "An Artist", f"September (feat. {artist_whitelist[0]})"
                )
            )
            == 2
        )
        assert (
            len(
                self.plugin.get_artists(
                    "An Artist", f"September (featuring {artist_whitelist[0]})"
                )
            )
            == 2
        )
        assert (
            len(
                self.plugin.get_artists(
                    "An Artist", f"September (with {artist_whitelist[0]})"
                )
            )
            == 2
        )

        artist_whitelist = ["Jim with Bob", "Earth, Wind & Fire"]
        self._setup_config(single_artists=artist_whitelist)
        assert len(self.plugin.get_artists(artist_whitelist[0], "September")) == 1

        artist_whitelist = [
            "AC/DC",
            "Daryl Hall & John Oates",
            "Earth, Wind & Fire",
            "Simon & Garfunkel",
            "Prince and The Revolution",
            "Florence + the Machine",
            "A with B",
        ]
        self._setup_config(single_artists=artist_whitelist)
        for i in artist_whitelist:
            test_result = self.plugin.get_artists(i, "Song Title")
            try:
                assert test_result == [i]
            except AssertionError as e:
                print(f"Failed on test result: {test_result}")
                raise e
            test_result = self.plugin.get_artists(
                f"{i} feat. Another Artist", "Song Title"
            )
            try:
                assert test_result == [i, "Another Artist"]
            except AssertionError as e:
                print(f"Failed on test result: {test_result}")
                raise e
            for test_result in [
                self.plugin.get_artists(f"B", f"Song Title (feat. {i})"),
                self.plugin.get_artists(f"B", f"Song Title (featuring {i})"),
                self.plugin.get_artists(f"B", f"Song Title (with {i})"),
            ]:
                try:
                    assert test_result == ["B", i]
                except AssertionError as e:
                    print(f"Failed on test result: {test_result}")
                    raise e
            # Test with 2 featured artists
            for separator in [", ", " & ", " + ", "/"]:
                for test_result in [
                    self.plugin.get_artists(
                        f"B", f"Song Title (feat. {i}{separator}OtherArtist)"
                    ),
                    self.plugin.get_artists(
                        f"B", f"Song Title (featuring {i}{separator}OtherArtist)"
                    ),
                    self.plugin.get_artists(
                        f"B", f"Song Title (with {i}{separator}OtherArtist)"
                    ),
                ]:
                    try:
                        assert test_result in [
                            ["B", i, "OtherArtist"],
                            ["B", "OtherArtist", i],
                        ]
                    except AssertionError as e:
                        print(f"Failed on test result: {test_result}")
                        raise e
            # Test with 3 featured artists
            for separator in [", ", " & ", " + "]:
                for test_result in [
                    self.plugin.get_artists(
                        f"B", f"Song Title (feat. {i}, AnArtist{separator}OtherArtist)"
                    ),
                    self.plugin.get_artists(
                        f"B",
                        f"Song Title (featuring {i}, AnArtist{separator}OtherArtist)",
                    ),
                    self.plugin.get_artists(
                        f"B", f"Song Title (with {i}, AnArtist{separator}OtherArtist)"
                    ),
                ]:
                    try:
                        assert sorted(test_result) == sorted(
                            ["B", i, "AnArtist", "OtherArtist"]
                        )
                    except AssertionError as e:
                        print(f"Failed on test result: {sorted(test_result)}")
                        raise e

    def test_separating_artist(self):
        self.setUp()
        artist_whitelist = ["Earth, Wind & Fire"]
        self._setup_config(single_artists=artist_whitelist)
        # Beyoncé feat. JAY-Z & Kanye West - BEYONCÉ (platinum edition) - Drunk in Love (remix)
        test_result = self.plugin.get_artists(
            artist="Beyoncé feat. JAY-Z & Kanye West", title="Drunk in Love (remix)"
        )
        assert test_result == ["Beyoncé", "JAY-Z", "Kanye West"]
        for test in [
            ("Jim Croce and Another artist", "a song title"),
            ("Jim Croce & Another artist", "a song title"),
            ("Jim Croce with Another artist", "a song title"),
            (f"Jim Croce feat. Another artist", "a song title"),
        ]:
            test_result = self.plugin.get_artists(test[0], test[1])
            try:
                assert test_result == ["Jim Croce", "Another artist"]
            except AssertionError as e:
                print(f"Failed on test result: {test_result}")
                raise e
        # Test the whitelist is respected:
        for test in [
            (f"Jim Croce and {artist_whitelist[0]}", "a song title"),
            (f"Jim Croce & {artist_whitelist[0]}", "a song title"),
            (f"Jim Croce with {artist_whitelist[0]}", "a song title"),
            (f"Jim Croce feat. {artist_whitelist[0]}", "a song title"),
        ]:
            test_result = self.plugin.get_artists(test[0], test[1])
            try:
                assert test_result == ["Jim Croce", {artist_whitelist[0]}] or [
                    {artist_whitelist[0]},
                    "Jim Croce",
                ]
            except AssertionError as e:
                print(f"Failed on test result: {test_result}")
                raise e
        # Make sure song titles with the word "With" are not counted as an
        # artist, unless the word "with" is the first word in () or []
        for test_result in [
            self.plugin.get_artists(f"Taylor Swift", f"You Belong With Me"),
        ]:
            try:
                assert test_result == ["Taylor Swift"]
            except AssertionError as e:
                print(f"Failed with test result: {test_result}")
                raise e
        # test that the word "with" inside () but not the first word will not be considered another artist
        for test_result in [
            self.plugin.get_artists(
                f"Kate Bush", "Running Up That Hill (A Deal with God)"
            ),
        ]:
            try:
                assert test_result == ["Kate Bush"]
            except AssertionError as e:
                print(f"Failed with test result: {test_result}")
                raise e
        # Testing that "title (feat. X) (something else)" is interpreted correctly
        for test_result in [
            self.plugin.get_artists(
                f"Taylor Swift", f"Breathe (feat. Colbie Caillat) (Taylor’s version)"
            ),
        ]:
            try:
                assert test_result == ["Taylor Swift", "Colbie Caillat"]
            except AssertionError as e:
                print(f"Failed with test result: {test_result}")
                raise e
        for test_result in [
            self.plugin.get_artists(f"Artist A", f"Song Title (With Artist B)"),
            self.plugin.get_artists(f"Artist A", f"Song Title (with Artist B)"),
            self.plugin.get_artists(f"Artist A", f"Song Title [With Artist B]"),
            self.plugin.get_artists(f"Artist A", f"Song Title [with Artist B]"),
            self.plugin.get_artists(f"Artist A", f"Song Title (feat Artist B)"),
            self.plugin.get_artists(f"Artist A", f"Song Title (Feat Artist B)"),
            self.plugin.get_artists(f"Artist A", f"Song Title (feat. Artist B)"),
            self.plugin.get_artists(f"Artist A", f"Song Title (Feat. Artist B)"),
            self.plugin.get_artists(f"Artist A", f"Song Title (featuring Artist B)"),
            self.plugin.get_artists(f"Artist A", f"Song Title (Featuring Artist B)"),
        ]:
            try:
                assert test_result == ["Artist A", "Artist B"]
            except AssertionError as e:
                print(f"Failed on test result: {test_result}")
                raise e
        try:
            assert (
                len(
                    self.plugin.get_artists(
                        "Taylor Swift",
                        "Safe & Sound (feat. Joy Williams and John Paul White) (Taylor’s Version)",
                        artists=["Taylor Swift", "Joy Williams", " John Paul White"],
                    )
                )
                == 3
            )
            assert (
                len(
                    self.plugin.get_artists(
                        "Taylor Swift",
                        "Safe & Sound (feat. Joy Williams and John Paul White) (Taylor’s Version)",
                        artists=[
                            "Taylor Swift",
                            "Joy Williams",
                            "John Paul White",
                            " John Paul White",
                        ],
                    )
                )
                == 3
            )
        except AssertionError as e:
            raise e
        for test_result in [
            self.plugin.get_artists(f"ZArtist A", f"Song Title (With Artist B)"),
            self.plugin.get_artists(
                f"ZArtist A & Artist B", f"Song Title (With Artist B)"
            ),
            self.plugin.get_artists(
                f"ZArtist A Feat. Artist B", f"Song Title (With Artist B)"
            ),
        ]:
            try:
                assert test_result == ["ZArtist A", "Artist B"]
            except AssertionError as e:
                print(f"Failed on test result: {test_result}")
                raise e
        for test_result in [
            self.plugin.get_artists(
                f"ZArtist A", f"Song Title (With Artist B and artist c)"
            ),
            self.plugin.get_artists(
                f"ZArtist A & Artist B, artist c", f"Song Title (With Artist B)"
            ),
            self.plugin.get_artists(
                f"ZArtist A Feat. Artist B & artist c", f"Song Title (With Artist B)"
            ),
        ]:
            try:
                assert test_result == ["ZArtist A", "Artist B", "artist c"]
            except AssertionError as e:
                print(f"Failed on test result: {test_result}")
                raise e


test = AutoArtistsPluginTest()
test.test_whitelist()
test.test_separating_artist()

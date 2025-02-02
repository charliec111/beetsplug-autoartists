# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.


import re
import unicodedata
import beets
from beets import config
from beets.dbcore import types
from beets.ui import decargs, print_, should_write
from beets.plugins import BeetsPlugin



class AutoArtistsPlugin(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.config.add(
            {
                "auto": False,
                "overwrite": True,
                "separators": ["␟", ", ", " & ", " and ", " + ", " with ", "/", ";"],
                "single_artists": []
            }
        )
        self.item_types = {
        }
        # self.single_artist_list is a list of artists who should not be broken up into multiples, 
        # see readme for more info
        self.overwrite = self.config["overwrite"]
        self.single_artist_list = [ x.as_str() for x in self.config["single_artists"] ]
        self.separators = [ x.as_str() for x in self.config["separators"]]
        if self.config["auto"]:
            self.import_stages = [self.imported]
        self._log.debug(f"Single artist list: {self.single_artist_list}")

    def commands(self):
        autoartists = beets.ui.Subcommand("autoartists", help="autoartists")
        autoartists.parser.add_option(
            "--no-overwrite",
            dest="dontoverwrite",
            action="store_true",
            default=False,
            help="Don't overwrite if artists field is already present (overrule config file overwrite: True)",
        )
        autoartists.parser.add_option(
            "--overwrite",
            dest="overwrite",
            action="store_true",
            default=False,
            help="Overwrite if artists field is already present (overrule config file overwrite: False)",
        )
        autoartists.func = self.exec_autoartists
        return [autoartists]

    def exec_autoartists(self, lib, opts, args):
        if opts.overwrite and opts.dontoverwrite:
            self._log.error("Can't specify --overwrite and --no-overwrite")
            exit(1)
        elif opts.overwrite:
            self.overwrite = True
        elif opts.dontoverwrite:
            self.overwrite = False
        # options override config settings:
        query_result_songs = lib.items(decargs(args))
        # choices is a list of tuples of (song, artists list) for each match in the query
        choices = []
        if not self.overwrite:
            query_result_songs = [ x for x in query_result_songs if "artists" not in x or len(x["artists"]) < 1 ]
        for song in query_result_songs:
            artist = str(song["artist"])
            title = str(song["title"])
            artists = None if "artists" not in song else song["artists"]
            artists_result = self.get_artists(artist=artist, title=title,artists=artists)
            choices.append((song,artists_result))

        old_choices_len = len(choices)
        new_choices = [ choice for choice in choices if "artists" not in choice[0] or not lists_have_same_strings(choice[0]["artists"], choice[1]) ]
        unchanged_choices = [ choice for choice in choices if choice not in new_choices ]
        choices = new_choices
        overwrite_message = ""
        if not self.overwrite: overwrite_message =" that would not be overwritten"
        print_(f"{old_choices_len} found in query{overwrite_message}, {old_choices_len - len(choices)} had no changes")
        if len(choices) == 0:
            if old_choices_len > 0:
                print_("Nothing to change")
            else:
                print_("No results found")
            exit()
        if len(unchanged_choices) > 0:
            print_("Unchanged:")
        for choice in unchanged_choices:
            song = choice[0]
            final_list = choice[1]
            artists=[ ]
            if "artists" in song:
                artists=song["artists"]
            print_(f"{song}: {artists}")
        print_("---")
        print_("Changes:")
        for choice in choices:
            song = choice[0]
            final_list = choice[1]
            artists=[  ]
            if "artists" in song:
                artists=song["artists"]
            print_(f"{song}: ")
            print_(f"old: {artists} => new: {final_list}")

        confirm = input(
            f"Changing {len(choices)} items. Confirm? (yes/no/select)\n"
        ).lower()
        if confirm in ["y", "yes"]:
            keep_asking = False
            confirm_item = ""
        elif confirm in ["s", "select"]:
            keep_asking = True
            confirm_item = ""
        else:
            print_("canceled")
            exit()
        for choice in choices:
            song = choice[0]
            final_list = choice[1]
            artists=[ "" ]
            if "artists" in song:
                artists=song["artists"]
            if keep_asking:
                print_(f"---")
                print_(f"{song}: " + str(final_list))
                confirm_item = input(
                    f"Changing from {artists} => new: {final_list}. Confirm? (y/n)\n"
                ).lower()
            if not lists_have_same_strings(artists, final_list) and (not keep_asking or confirm_item in ["y", "yes"]):
                song["artists"] = final_list
                if should_write():
                    song.try_write()
                song.store()
    # input: artist and title are strings from the song, artists is the list of 
    # strings of artist names the song already has or None
    # output: returns a list of strings of artists correspoding to the artist/title/artists
    def get_artists(self,artist, title, artists=None):
        auto_artists = []
        if artists:
            auto_artists = auto_artists + artists
        for single_artist in self.single_artist_list:
            if single_artist.lower() in artist.lower():
                self._log.debug(f"single artist {single_artist}: {artist}")
                if single_artist not in auto_artists:
                    auto_artists = auto_artists + [single_artist]
                artist = re.sub(re.escape(single_artist),"",artist, re.IGNORECASE)
                self._log.debug(f"artist is now {artist}")
        for i in [ "(feat. ", "(featuring ", "(with " ]:
            if i in artist.lower():
                artist = re.sub(
                    r"(.*) *[\(\[](feat\.|with|featuring) ([^)\]]*)[\)\]].*$",
                    r"\1, \3",
                    artist,
                    flags=re.IGNORECASE,
                )
        for i in [" feat. ", " featuring ", " Feat. ", " Featuring "]:
            if i in artist:
                artist = artist.replace(i, ", ")
        for new_artist in split_artists_string(artist,self.single_artist_list, separators=self.separators):
            if new_artist not in auto_artists:
                self._log.debug(f"Adding artist {new_artist}")
                auto_artists.append(new_artist)
        if re.match (
            r".* [\(\[](feat\.?|with|featuring) ([^)\]]*)[\)\]].*",
            title,
            re.IGNORECASE
        ):
            featured_artist_string = re.sub(
                r".*[\(\[](feat\.?|with|featuring) ([^)\]]*)[\)\]].*$",
                r"\2",
                title,
                flags=re.IGNORECASE,
            )
            featured_artists = split_artists_string(featured_artist_string, self.single_artist_list, separators=self.separators)
            auto_artists = auto_artists + [ x for x in featured_artists if x not in auto_artists ]

        auto_artists = [ x.strip() for x in auto_artists ]

        #final cleanups
        final_list = []
        normalized_artists_strings = []
        for auto_artist in auto_artists:
            normalized_artist = normalize_string(auto_artist)
            if (
                auto_artist.lower() != "various artists"
                and auto_artist not in final_list
                and len(auto_artist) > 0
                and normalized_artist not in normalized_artists_strings
            ):
                normalized_artists_strings.append(normalized_artist)
                # Put the track artist first, otherwise add at the end
                if auto_artist == artist:
                    final_list.insert(0,auto_artist)
                else:
                    final_list.append(auto_artist)
        return final_list
    def imported(self, session, task):
        for song in task.imported_items():
            artist = str(song["artist"])
            title = str(song["title"])
            existing_artists = None if "artists" not in song else song["artists"]
            artists_result = self.get_artists(artist=artist, title=title,artists=existing_artists)
            self._log.info(f"Autoartists: {song} has artists {existing_artists}")
            if not lists_have_same_strings(existing_artists, artists_result): 
                song["artists"] = artists_result
                if should_write():
                    song.try_write()
                song.store()
                self._log.info(f"Autoartists: Added artists {artists_result} to {song}")
# Input: artists_string is a string with one or multiple artists
# single_artists is a list of strings which should be treated as one artist (do not separate them)
# Output: A list of strings of the artist names in artists_string
def split_artists_string(artists_string,single_artists, separators=["␟", ", ", " & ", " and ", " + ", " with ", "/", ";"]):
    separator=separators[0]
    other_separators=separators[1:]
    artists = []
    for artist in single_artists:
        if artist.lower() in artists_string.lower():
            artists.append(artist)
            if artist.lower() == artists_string.lower():
                artists_string = ""
                return artists
            else:
                artists_string = re.sub(re.escape(artist),"",artists_string, re.IGNORECASE)
    for i in other_separators:
        artists_string = artists_string.replace(i, separator)
    artists = [ x for x in (artists_string.split(separator) + artists) if x not in ["", " "]]
    return artists

# a,b are lists of strings
# return True if every string in a is in b and vice versa, False otherwise
def lists_have_same_strings(a,b):
    if len(a) != len(b): return False
    lower_a = [ normalize_string(x) for x in a ]
    lower_b = [ normalize_string(x) for x in b ]
    diff = [ x for x in lower_a if x not in lower_b ] + [ x for x in lower_b if x not in lower_a ]
    return not len(diff) > 0
# This function is mostly copied from a project called maloja by krateng
# most of it is unnecessary, it's copied and pasted from my uses of it in
# other projects where song artists/tracks strings are normalized and compared
def normalize_string(string_in):
    new_string = string_in.lower()
    remove_symbols = ["'", "`", "’"]
    replace_with_space = [" - ", ": "]
    for r in replace_with_space:
        new_string = new_string.replace(r, " ")
    new_string = "".join(
        char
        for char in unicodedata.normalize("NFD", new_string.lower())
        if char not in remove_symbols and unicodedata.category(char) != "Mn"
    )
    new_string = (
        new_string.replace("’", "'")
        .replace("…", "...")
        .replace("‐", "-")
        .replace("  ", " ")
    )
    # new_string = re.sub(r"  *", " ", new_string)
    return new_string
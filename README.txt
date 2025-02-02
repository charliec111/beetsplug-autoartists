autoartists is a beetbox beets plugin to fill the artists field from parsing the 
artist, title (for featured artists). Beets writes artists to the file as a multivalued tag.

Install with pip install git+https://github.com/charliec111/beetsplug-autoartists.git

I wrote this because I use ftintitle to match last.fm
[so songs are tagged as artist: "ArtistA", title: "title (feat. ArtistB)]
and I wanted multivalued tags for the players that support it (particularly
the upcoming version of navidrome).
Use with risk. I haven't extensively tested this. This will prompt yes/no/select
to allow you to review its changes before writing.

Artists that contain a separator string may be mistakenly treated as multiple artists. 
default separator strings are [ "␟", ", ", " & ", " and ", " + ", " with ", "/", ";" ]
The separator strings can be specified in the config.
To always treat an artist as a single artist (never split), add it to single_artists to the config.
auto: True/False controls whether to run on import
overwrite: False will ignore files when the artists field is already filled.
config example:

autoartists:
  auto: True
  overwrite: True
  single_artists:                                                                                                                                                                                           
    - Daryl Hall & John Oates                                                                     
    - Earth, Wind & Fire                                                                          
    - Simon & Garfunkel                                                                           
    - Prince and The Revolution                                                                                                                                                                      
    - Florence + the Machine                                                                                                                                                                         
    - Tom Petty and the Heartbreakers                                                             
    - AC/DC 
  separators: ["␟", ", ", " & ", " and ", " + ", " with ", "/", ";"]
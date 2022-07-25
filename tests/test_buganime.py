from buganime.buganime import parse_filename, TVShow

NAME_CONVERSIONS = [
    (r'C:\[SHiN-gx] Fight Ippatsu! Juuden-chan!! - Special 1 [720x480 AR h.264 FLAC][v2][FF09021F].mkv',
     TVShow(name='Fight Ippatsu! Juuden-chan!!', season=0, episode=1)),

    (r'C:\[gleam] Kurenai OVA - 01 [OAD][0e73f000].mkv',
     TVShow(name='Kurenai', season=0, episode=1)),

    (r'C:\[Jarzka] Saki Picture Drama 1 [480p 10bit DVD FLAC] [BA3CE364].mkv',
     TVShow(name='Saki', season=0, episode=1)),

    (r'C:\[CoalGuys] K-ON!! S2 - 05 [4B19B10F].mkv',
     TVShow(name='K-ON!!', season=2, episode=5)),

    (r'C:\[SubsPlease] RWBY - Hyousetsu Teikoku - 01 (1080p) [FA9C5B87].mkv',
     TVShow(name='RWBY - Hyousetsu Teikoku', season=1, episode=1)),

    (r'C:\[SubsPlease] Tokyo Mew Mew New - 01 (1080p) [440C0CD7].mkv',
     TVShow(name='Tokyo Mew Mew New', season=1, episode=1)),

    (r'C:\[Erai-raws] Shin Tennis no Ouji-sama - U-17 World Cup - 01 [1080p][Multiple Subtitle][0341CBE1].mkv',
     TVShow(name='Shin Tennis no Ouji-sama - U-17 World Cup', season=1, episode=1)),

    (r'C:\[Judas] Kaguya-Sama Wa Kokurasetai - S03E07.mkv',
     TVShow(name='Kaguya-Sama Wa Kokurasetai', season=3, episode=7)),

    (r'C:\[SubsPlease] Rikei ga Koi ni Ochita no de Shoumei shitemita - 08v2 (1080p) [77514EF3].mkv',
     TVShow(name='Rikei ga Koi ni Ochita no de Shoumei shitemita', season=1, episode=8)),

    (r'C:\[SubsPlease] Rikei ga Koi ni Ochita no de Shoumei shitemita S2 - 08v2 (1080p) [77514EF3].mkv',
     TVShow(name='Rikei ga Koi ni Ochita no de Shoumei shitemita', season=2, episode=8)),

    (r'C:\Kaguya-sama - Love is War - S00E01 - (S2O1 OVA).mkv',
     TVShow(name='Kaguya-sama - Love is War', season=0, episode=1)),

    (r'C:\Kaguya-sama - Love is War - S01E06.mkv',
     TVShow(name='Kaguya-sama - Love is War', season=1, episode=6)),

    (r'C:\Kaguya-sama wa Kokurasetai S03 1080p Dual Audio WEBRip AAC x265-EMBER\S03E01-Miko Iino Wants to Be Soothed Kaguya '
        r'Doesn’t Realize Chika Fujiwara Wants to Battle [8933E8C9].mkv',
     TVShow(name='Kaguya-sama wa Kokurasetai', season=3, episode=1)),
]


def test_parse_filename() -> None:
    for path, result in NAME_CONVERSIONS:
        assert parse_filename(path) == result

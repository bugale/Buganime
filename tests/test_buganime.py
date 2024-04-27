import os
import tempfile
import json
from buganime import buganime, transcode

NAME_CONVERSIONS = [
    (r'C:\[SHiN-gx] Fight Ippatsu! Juuden-chan!! - Special 1 [720x480 AR h.264 FLAC][v2][FF09021F].mkv',
     buganime.TVShow(name='Fight Ippatsu! Juuden-chan!!', season=0, episode=1)),

    (r'C:\[gleam] Kurenai OVA - 01 [OAD][0e73f000].mkv',
     buganime.TVShow(name='Kurenai', season=0, episode=1)),

    (r'C:\[Jarzka] Saki Picture Drama 1 [480p 10bit DVD FLAC] [BA3CE364].mkv',
     buganime.TVShow(name='Saki', season=0, episode=1)),

    (r'C:\[CoalGuys] K-ON!! S2 - 05 [4B19B10F].mkv',
     buganime.TVShow(name='K-ON!!', season=2, episode=5)),

    (r'C:\[SubsPlease] RWBY - Hyousetsu Teikoku - 01 (1080p) [FA9C5B87].mkv',
     buganime.TVShow(name='RWBY - Hyousetsu Teikoku', season=1, episode=1)),

    (r'C:\[SubsPlease] Tokyo Mew Mew New - 01 (1080p) [440C0CD7].mkv',
     buganime.TVShow(name='Tokyo Mew Mew New', season=1, episode=1)),

    (r'C:\[Erai-raws] Shin Tennis no Ouji-sama - U-17 World Cup - 01 [1080p][Multiple Subtitle][0341CBE1].mkv',
     buganime.TVShow(name='Shin Tennis no Ouji-sama - U-17 World Cup', season=1, episode=1)),

    (r'C:\[Judas] Kaguya-Sama Wa Kokurasetai - S03E07.mkv',
     buganime.TVShow(name='Kaguya-Sama Wa Kokurasetai', season=3, episode=7)),

    (r'C:\[SubsPlease] Rikei ga Koi ni Ochita no de Shoumei shitemita - 08v2 (1080p) [77514EF3].mkv',
     buganime.TVShow(name='Rikei ga Koi ni Ochita no de Shoumei shitemita', season=1, episode=8)),

    (r'C:\[SubsPlease] Rikei ga Koi ni Ochita no de Shoumei shitemita S2 - 08v2 (1080p) [77514EF3].mkv',
     buganime.TVShow(name='Rikei ga Koi ni Ochita no de Shoumei shitemita', season=2, episode=8)),

    (r'C:\Kaguya-sama - Love is War - S00E01 - (S2O1 OVA).mkv',
     buganime.TVShow(name='Kaguya-sama - Love is War', season=0, episode=1)),

    (r'C:\Kaguya-sama - Love is War - S01E06.mkv',
     buganime.TVShow(name='Kaguya-sama - Love is War', season=1, episode=6)),

    (r'C:\Kaguya-sama wa Kokurasetai S03 1080p Dual Audio WEBRip AAC x265-EMBER\S03E01-Miko Iino Wants to Be Soothed Kaguya Doesn’t Realize Chika Fujiwara '
        r'Wants to Battle [8933E8C9].mkv',
     buganime.TVShow(name='Kaguya-sama wa Kokurasetai', season=3, episode=1)),

    (r'C:\Kaguya-sama wa Kokurasetai S2 - OVA - 1080p WEB H.264 -NanDesuKa (B-Global).mkv',
     buganime.TVShow(name='Kaguya-sama wa Kokurasetai', season=0, episode=1)),

    (r'C:\Tensei shitara Ken Deshita - 01 - 2160p WEB H.264 -NanDesKa.mkv',
     buganime.TVShow(name='Tensei shitara Ken Deshita', season=1, episode=1)),

    (r'C:\Watashi no Shiawase na Kekkon - S01E01 - MULTi.mkv',
     buganime.TVShow(name='Watashi no Shiawase na Kekkon', season=1, episode=1)),

    (r'C:\Monogatari Series\15. Zoku Owarimonogatari\Zoku Owarimonogatari 01 - Koyomi Reverse, Part 1.mkv',
     buganime.TVShow(name='Zoku Owarimonogatari', season=1, episode=1)),

    (r'C:\SNAFU S01-S03+OVA 1080p Dual Audio BDRip 10 bits DD x265-EMBER\SNAFU S02+OVA 1080p Dual Audio BDRip 10 bits DD x265-EMBER\Series\S02E01-Nobody Knows'
        r'Why They Came to the Service Club [7CE95AC0].mkv',
     buganime.TVShow(name='SNAFU', season=2, episode=1)),

    (r'C:\Temp\Torrents\SNAFU S01-S03+OVA 1080p Dual Audio BDRip 10 bits DD x265-EMBER\SNAFU S02+OVA 1080p Dual Audio BDRip 10 bits DD x265-EMBER\OVA\S02E14 '
        r'[OVA]-Undoubtedly, Girls Are Made of Sugar, Spice, and Everything Nice [7E9E8A1F].mkv',
     buganime.TVShow(name='SNAFU', season=2, episode=14)),
]


STREAM_CONVERSIONS = [
    ('0.json', transcode.VideoInfo(audio_index=1, subtitle_index=1, width=1920, height=1080, fps='24000/1001', frames=34094)),
    ('1.json', transcode.VideoInfo(audio_index=1, subtitle_index=3, width=1920, height=1080, fps='24000/1001', frames=34095)),
    ('2.json', transcode.VideoInfo(audio_index=1, subtitle_index=0, width=1920, height=1080, fps='24000/1001', frames=34046)),
    ('3.json', transcode.VideoInfo(audio_index=1, subtitle_index=0, width=1920, height=1080, fps='24000/1001', frames=34045)),
    ('4.json', transcode.VideoInfo(audio_index=2, subtitle_index=1, width=1920, height=1080, fps='24000/1001', frames=34047)),
    ('5.json', transcode.VideoInfo(audio_index=2, subtitle_index=1, width=1920, height=1080, fps='24000/1001', frames=35638)),
    ('6.json', transcode.VideoInfo(audio_index=1, subtitle_index=0, width=1920, height=1080, fps='30/1', frames=7425)),
    ('7.json', transcode.VideoInfo(audio_index=1, subtitle_index=0, width=1920, height=1080, fps='24000/1001', frames=0)),
]


def test_parse_filename() -> None:
    for path, result in NAME_CONVERSIONS:
        assert buganime.parse_filename(path) == result


def test_parse_streams() -> None:
    for filename, result in STREAM_CONVERSIONS:
        with open(os.path.join(os.path.dirname(__file__), 'data', filename), 'rb') as file:
            assert buganime.parse_streams(json.loads(file.read())['streams']) == result


def test_sanity() -> None:
    with tempfile.TemporaryDirectory() as tempdir:
        buganime.OUTPUT_DIR = tempdir
        buganime.process_file(os.path.join(os.path.dirname(__file__), 'data', '0.mkv'))

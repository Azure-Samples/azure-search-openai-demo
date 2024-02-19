def get_video_url(isp_path, is_bot_male, is_patient_male, video_index):
    return videos[isp_path]["maleBot" if is_bot_male else "femaleBot"]["malePatient" if is_patient_male else "femalePatient"][video_index]

videos = {
    "1": {
        "femaleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/900614389?h=e0ad38f99b",
                "https://player.vimeo.com/video/900616383?h=54b5dc0138",
                "https://player.vimeo.com/video/900617581?h=ed2da63cac",
                "https://player.vimeo.com/video/900618500?h=61e6bf2ffb",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/900704349?h=0386e8b0ea",
                "https://player.vimeo.com/video/900704370?h=42ed517aaa",
                "https://player.vimeo.com/video/900704387?h=c06fedb1c3",
                "https://player.vimeo.com/video/900704402?h=1eeb583948",
            ]
        },
        "maleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/897559149?h=4a55875501",
                "https://player.vimeo.com/video/897557836?h=c5dfc0a1f9",
                "https://player.vimeo.com/video/897555279?h=16729fcb49",
                "https://player.vimeo.com/video/897556460?h=5d2bbdd7c3",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/895974469?h=3d6110590b",
                "https://player.vimeo.com/video/895970401?h=c71ded78f9",
                "https://player.vimeo.com/video/895972299?h=87d1a92598",
                "https://player.vimeo.com/video/895968595?h=ff4542ca43",
            ]
        }
    },
    "2": {
        "femaleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/900704686?h=81c7fc8be0",
                "https://player.vimeo.com/video/900704710?h=653bdddbed",
                "https://player.vimeo.com/video/900704723?h=9767a694e1",
                "https://player.vimeo.com/video/900704744?h=13ee2a4444",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/900704221?h=31467008bc",
                "https://player.vimeo.com/video/900706167?h=303126e536",
                "https://player.vimeo.com/video/900704253?h=5640603dc0",
                "https://player.vimeo.com/video/900704271?h=91e6ca68ce",
            ]
        },
        "maleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/897564810?h=21ad8840dd",
                "https://player.vimeo.com/video/897562332?h=a7513f991f",
                "https://player.vimeo.com/video/897563724?h=284b027a7b",
                "https://player.vimeo.com/video/897561328?h=5447fb4524",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/896006274?h=4815b4562d",
                "https://player.vimeo.com/video/896008746?h=466f3430d0",
                "https://player.vimeo.com/video/896004265?h=eb11658d20",
                "https://player.vimeo.com/video/896000466?h=a51e4f9b65",
            ]
        }
    },
    "3": {
        "femaleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/900704542?h=d041770ce3",
                "https://player.vimeo.com/video/900704563?h=d93bac95b4",
                "https://player.vimeo.com/video/900704588?h=0649c99d04",
                "https://player.vimeo.com/video/900704602?h=f4348ca13c",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/900704424?h=4570c6fa3b",
                "https://player.vimeo.com/video/900704482?h=dcf0e97a1a",
                "https://player.vimeo.com/video/900704506?h=0475d81986",
                "https://player.vimeo.com/video/900704527?h=ffa60fb685",
            ]
        },
        "maleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/897574889?h=31b7176a9b",
                "https://player.vimeo.com/video/897572422?h=47cf93205a",
                "https://player.vimeo.com/video/897573841?h=54ef745acf",
                "https://player.vimeo.com/video/897571339?h=3a8cccb816",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/895992824?h=8be8124fbe",
                "https://player.vimeo.com/video/895990902?h=bb9e364911",
                "https://player.vimeo.com/video/895987357?h=2d0a3f6249",
                "https://player.vimeo.com/video/895989491?h=d0ecbe98d2",
            ]
        }
    },
    "4": {
        "femaleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/900704618?h=a725473863",
                "https://player.vimeo.com/video/900704642?h=ecf4358965",
                "https://player.vimeo.com/video/900704657?h=11e01297ce",
                "https://player.vimeo.com/video/900704671?h=3d0f90424c",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/900704298?h=cdf8ae67a5",
                "https://player.vimeo.com/video/900704316?h=b79f67eaf1",
                "https://player.vimeo.com/video/900704282?h=40246e20f6",
                "https://player.vimeo.com/video/900704336?h=9b1a21c4f7",
            ]
        },
        "maleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/897569924?h=4f520e7b8f",
                "https://player.vimeo.com/video/897568139?h=06e853fcec",
                "https://player.vimeo.com/video/897569105?h=11c88b14c7",
                "https://player.vimeo.com/video/897567127?h=4442a846ea",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/895982402?h=4e308bb1e0",
                "https://player.vimeo.com/video/895978161?h=6c2fc21264",
                "https://player.vimeo.com/video/895980650?h=2de6511c91",
                "https://player.vimeo.com/video/895985710?h=71fb7f77f9",
            ]
        }
    },
    "5": {
        "femaleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/900704757?h=60e0cdb329",
                "https://player.vimeo.com/video/900704774?h=5816ff6cae",
                "https://player.vimeo.com/video/900704798?h=26ffd3bfc8",
                "https://player.vimeo.com/video/900704815?h=1ab0f3fce4",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/900609607?h=2258aaa05d",
                "https://player.vimeo.com/video/900610978?h=2440bec5a9",
                "https://player.vimeo.com/video/900612119?h=7a2b15775b",
                "https://player.vimeo.com/video/900613199?h=cf5fab2622",
            ]
        },
        "maleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/897580251?h=a2f54e56d5",
                "https://player.vimeo.com/video/897577581?h=803559991e",
                "https://player.vimeo.com/video/897578894?h=6dcdb0cc86",
                "https://player.vimeo.com/video/897576687?h=90598b74a5",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/896002079?h=7b6bd078ad",
                "https://player.vimeo.com/video/895998785?h=60c44627c9",
                "https://player.vimeo.com/video/895995866?h=5361d0b775",
                "https://player.vimeo.com/video/895997267?h=4530c5099b",
            ]
        }
    }
}

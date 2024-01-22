def get_video_url(isp_path, is_bot_male, is_patient_male, video_index):
    return videos[isp_path]["maleBot" if is_bot_male else "femaleBot"]["malePatient" if is_patient_male else "femalePatient"][video_index]

videos = {
    "1": {
        "femaleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/900614389",
                "https://player.vimeo.com/video/900616383",
                "https://player.vimeo.com/video/900617581",
                "https://player.vimeo.com/video/900618500",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/900704349",
                "https://player.vimeo.com/video/900704370",
                "https://player.vimeo.com/video/900704387",
                "https://player.vimeo.com/video/900704402",
            ]
        },
        "maleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/897559149",
                "https://player.vimeo.com/video/897557836",
                "https://player.vimeo.com/video/897555279",
                "https://player.vimeo.com/video/897556460",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/895974469",
                "https://player.vimeo.com/video/895970401",
                "https://player.vimeo.com/video/895972299",
                "https://player.vimeo.com/video/895968595",
            ]
        }
    },
    "2": {
        "femaleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/900704686",
                "https://player.vimeo.com/video/900704710",
                "https://player.vimeo.com/video/900704723",
                "https://player.vimeo.com/video/900704744",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/900704221",
                "https://player.vimeo.com/video/900706167",
                "https://player.vimeo.com/video/900704253",
                "https://player.vimeo.com/video/900704271",
            ]
        },
        "maleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/897564810",
                "https://player.vimeo.com/video/897562332",
                "https://player.vimeo.com/video/897563724",
                "https://player.vimeo.com/video/897561328",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/896006274",
                "https://player.vimeo.com/video/896008746",
                "https://player.vimeo.com/video/896004265",
                "https://player.vimeo.com/video/896000466",
            ]
        }
    },
    "3": {
        "femaleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/900704542",
                "https://player.vimeo.com/video/900704563",
                "https://player.vimeo.com/video/900704588",
                "https://player.vimeo.com/video/900704602",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/900704424",
                "https://player.vimeo.com/video/900704482",
                "https://player.vimeo.com/video/900704506",
                "https://player.vimeo.com/video/900704527",
            ]
        },
        "maleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/897574889",
                "https://player.vimeo.com/video/897572422",
                "https://player.vimeo.com/video/897573841",
                "https://player.vimeo.com/video/897571339",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/895992824",
                "https://player.vimeo.com/video/895990902",
                "https://player.vimeo.com/video/895987357",
                "https://player.vimeo.com/video/895989491",
            ]
        }
    },
    "4": {
        "femaleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/900704618",
                "https://player.vimeo.com/video/900704642",
                "https://player.vimeo.com/video/900704657",
                "https://player.vimeo.com/video/900704671",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/900704298",
                "https://player.vimeo.com/video/900704316",
                "https://player.vimeo.com/video/900704282",
                "https://player.vimeo.com/video/900704336",
            ]
        },
        "maleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/897569924",
                "https://player.vimeo.com/video/897568139",
                "https://player.vimeo.com/video/897569105",
                "https://player.vimeo.com/video/897567127",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/895982402",
                "https://player.vimeo.com/video/895978161",
                "https://player.vimeo.com/video/895980650",
                "https://player.vimeo.com/video/895985710",
            ]
        }
    },
    "5": {
        "femaleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/900704757",
                "https://player.vimeo.com/video/900704774",
                "https://player.vimeo.com/video/900704798",
                "https://player.vimeo.com/video/900704815",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/900609607",
                "https://player.vimeo.com/video/900610978",
                "https://player.vimeo.com/video/900612119",
                "https://player.vimeo.com/video/900613199",
            ]
        },
        "maleBot": {
            "femalePatient": [
                "https://player.vimeo.com/video/897580251",
                "https://player.vimeo.com/video/897577581",
                "https://player.vimeo.com/video/897578894",
                "https://player.vimeo.com/video/897576687",
            ],
            "malePatient": [
                "https://player.vimeo.com/video/896002079",
                "https://player.vimeo.com/video/895998785",
                "https://player.vimeo.com/video/895995866",
                "https://player.vimeo.com/video/895997267",
            ]
        }
    }
}

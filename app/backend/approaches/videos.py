def get_video(isp_path, is_bot_male, is_patient_male, video_index):
    return videos[isp_path]["maleBot" if is_bot_male else "femaleBot"]["malePatient" if is_patient_male else "femalePatient"][video_index]

videos = {
    "1": {
        "femaleBot": {
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

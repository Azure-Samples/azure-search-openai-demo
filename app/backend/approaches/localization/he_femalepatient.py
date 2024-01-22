from approaches.localization.he import choose_annoying_reason, exit_no_distress, had_improvement, he, how_much_distress, no_distress_on_start, should_continue_after_distress_increased, should_continue_after_no_change, wait_input_before_video, wrong_annoying_reason, wrong_distress_level

heFemalePatient = {
    "id": "heFemalePatient",
    "parent": he["id"],
    "howMuchDistress": how_much_distress(is_patient_male=False),
    "noDistressOnStart": no_distress_on_start(is_patient_male=False),
    "wrongDistressLevel": wrong_distress_level(is_patient_male=False),
    "wrongInputYesNo": "לא הבנתי את תשובתך. אנא הקלידי כן/לא",
    "exitNoDistress": exit_no_distress(is_patient_male=False),
    "chooseAnnoyingReasonWithLowDistress": [{"role": "explanationText", "content": choose_annoying_reason(is_patient_male=False)}],
    "wrongAnnoyingReason": wrong_annoying_reason(is_patient_male=False),
    "waitInputBeforeVideo": wait_input_before_video(is_patient_male=True),
    "shouldContinueAfterNoChange": should_continue_after_no_change(is_patient_male=False),
    "shouldContinueAfterDistressIncreased": should_continue_after_distress_increased(is_patient_male=False),
    "hadImprovement": had_improvement(is_patient_male=False),
}
from approaches.localization.he import choose_annoying_reason_with_distress, exit_after_distress_increased_and_fail_to_connect_to_current, exit_after_distress_increased_and_succeed_to_connect_to_current, exit_after_distress_increased_twice, exit_after_improvement, exit_after_improvement_and_fail_to_connect_to_current, exit_after_improvement_and_succeed_to_connect_to_current, exit_after_no_clear_improvement_and_fail_to_connect_to_current, exit_after_no_clear_improvement_and_succeed_to_connect_to_current, exit_no_clear_improvement, get_video_message, is_connected_to_current_after_improvement, is_connected_to_current_after_no_improvement, should_continue_after_improvement
from approaches.localization.he_femalepatient import heFemalePatient

heFemalePatientMaleBot = {
    "id": "heFemalePatientMaleBot",
    "parent": heFemalePatient["id"],
    "chooseAnnoyingReasonWithMediumDistress": [{"role": "explanationText", "content": choose_annoying_reason_with_distress(is_patient_male=False, is_bot_male=True, is_distress_high=False)}],
    "chooseAnnoyingReasonWithHighDistress": [{"role": "explanationText", "content": choose_annoying_reason_with_distress(is_patient_male=False, is_bot_male=True, is_distress_high=True)}],
    "videoUrl": lambda request_context: get_video_message(request_context, is_patient_male=False, is_bot_male=True),
    "exitAfterDistressIncreasedTwice": exit_after_distress_increased_twice(is_bot_male=True),
    "exitAfterImprovement": exit_after_improvement(is_patient_male=False, is_bot_male=True),
    "exitNoClearImprovement": exit_no_clear_improvement(is_patient_male=False, is_bot_male=True),
    "shouldContinueAfterImprovement": should_continue_after_improvement(is_patient_male=False, is_bot_male=True),
    "isConnectedToCurrentAfterNoImprovement": is_connected_to_current_after_no_improvement(is_patient_male=False, is_bot_male=True),
    "isConnectedToCurrentAfterImprovement": is_connected_to_current_after_improvement(is_patient_male=False, is_bot_male=True),
    "exitAfterDistressIncreasedAndFailToConnectToCurrent": exit_after_distress_increased_and_fail_to_connect_to_current(is_patient_male=False, is_bot_male=True),
    "exitAfterDistressIncreasedAndSucceedToConnectToCurrent": exit_after_distress_increased_and_succeed_to_connect_to_current(is_patient_male=False, is_bot_male=True),
    "exitAfterImprovementAndFailToConnectToCurrent": exit_after_improvement_and_fail_to_connect_to_current(is_patient_male=False, is_bot_male=True),
    "exitAfterImprovementAndSucceedToConnectToCurrent": exit_after_improvement_and_succeed_to_connect_to_current(is_patient_male=False, is_bot_male=True),
    "exitAfterNoClearImprovementAndFailToConnectToCurrent":  exit_after_no_clear_improvement_and_fail_to_connect_to_current(is_patient_male=False, is_bot_male=True),
    "exitAfterNoClearImprovementAndSucceedToConnectToCurrent": exit_after_no_clear_improvement_and_succeed_to_connect_to_current(is_patient_male=False, is_bot_male=True),
}
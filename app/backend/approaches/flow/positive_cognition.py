from approaches.flow.shared_states import ChatInputNotWait, ConditionedAction, State, StateExit, StateStartPositiveCognition, States, VariableExitText, VariableIsBotMale, VariableIsPatientMale, chat_input_multiple_options, is_exit_after_distress_increased, is_exit_after_improvement
from approaches.requestcontext import RequestContext

StateGetImprovement = "GET_IMPROVEMENT"
StateGetIsConnectedToCurrent = "GET_IS_CONNECTED_TO_CURRENT"

States[StateStartPositiveCognition] = State(chat_input=ChatInputNotWait, conditioned_actions=[
    ConditionedAction(condition=None, output="hadImprovement", next_state=StateGetImprovement, condition_description=None)
])

States[StateGetImprovement] = State(chat_input=chat_input_multiple_options(["ללא שיפור", "שיפור מועט", "שיפור קל", "שיפור בינוני", "שיפור גדול"]), conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: input.strip() in ("ללא שיפור", "ללא"), output="isConnectedToCurrentAfterNoImprovement", next_state=StateGetIsConnectedToCurrent, condition_description="המשתמש\ת בחר\ה ללא שיפור"),
    ConditionedAction(condition=lambda request_context, input: input.strip() in ("שיפור מועט", "שיפור קל", "שיפור בינוני", "שיפור גדול", "מועט", "קל", "בינוני", "גדול"), output="isConnectedToCurrentAfterImprovement", next_state=StateGetIsConnectedToCurrent, condition_description="המשתמש\ת בחר\ה שיפור מסוים"),
    ConditionedAction(condition=None, output="wrongHasImprovement", next_state=StateGetImprovement, condition_description=None),
])

def is_exit_after_fail_to_connect_to_current(input) -> bool:
    return input.strip() == "כלל לא"
def is_exit_after_succeed_to_connect_to_current(input) -> bool:
    return input.strip() in ["במידה מועטה", "במידה מתונה", "במידה רבה", "במידה רבה מאד"]
States[StateGetIsConnectedToCurrent] = State(chat_input=chat_input_multiple_options(["כלל לא", "במידה מועטה", "במידה מתונה", "במידה רבה", "במידה רבה מאד"]), conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: is_exit_after_distress_increased(request_context, input) and is_exit_after_fail_to_connect_to_current(input), output="exitAfterDistressIncreasedAndFailToConnectToCurrent", next_state=StateExit, condition_description="המשתמש\ת בחר\ה כלל לא, והייתה החרפה"),
    ConditionedAction(condition=lambda request_context, input: is_exit_after_distress_increased(request_context, input) and is_exit_after_succeed_to_connect_to_current(input), output="exitAfterDistressIncreasedAndSucceedToConnectToCurrent", next_state=StateExit, condition_description="המשתמש\ת בחר\ה הצלחה כלשהי להתחבר להווה, והייתה החרפה"),
    ConditionedAction(condition=lambda request_context, input: is_exit_after_improvement(request_context, input) and is_exit_after_fail_to_connect_to_current(input), output="exitAfterImprovementAndFailToConnectToCurrent", next_state=StateExit, condition_description="המשתמש\ת בחר\ה כלל לא, והייתה הטבה ברמת המצוקה"),
    ConditionedAction(condition=lambda request_context, input: is_exit_after_improvement(request_context, input) and is_exit_after_succeed_to_connect_to_current(input), output="exitAfterImprovementAndSucceedToConnectToCurrent", next_state=StateExit, condition_description="המשתמש\ת בחר\ה הצלחה כלשהי להתחבר להווה, והייתה הטבה ברמת המצוקה"),
    ConditionedAction(condition=lambda request_context, input: is_exit_after_fail_to_connect_to_current(input), output="exitAfterNoClearImprovementAndFailToConnectToCurrent", next_state=StateExit, condition_description="המשתמש\ת בחר\ה כלל לא, ולא ניתן להצביע על הטבה"),
    ConditionedAction(condition=lambda request_context, input: is_exit_after_succeed_to_connect_to_current(input), output="exitAfterNoClearImprovementAndSucceedToConnectToCurrent", next_state=StateExit, condition_description="המשתמש\ת בחר\ה הצלחה כלשהי להתחבר להווה, ולא ניתן להצביע על הטבה"),
    ConditionedAction(condition=None, output="wrongIsConnectedToCurrent", next_state=StateGetIsConnectedToCurrent, condition_description=None)
])
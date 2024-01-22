from approaches.flow.shared_states import ChatInputNotWait, ConditionedAction, State, StateChooseExitText, StateExit, StateStartISP, StateStartPositiveCognition, States, VariableDistressLevel, VariableIsUserExited, VariableIspPath, VariablePrevDistressLevel, VariableSumDistressLevel, VariableVideoIndex, VariableWasDistressLevelIncreased, VariableWasDistressLevelIncreasedTwice, chat_input_multiple_options, chat_input_numeric
from approaches.requestcontext import RequestContext

StateWaitForResponseBeforeVideo = "WAIT_FOR_RESPONSE_BEFORE_VIDEO"
StateShowVideo = "SHOW_VIDEO"
StateGetIfToContinueAfterVideo = "GET_IF_TO_CONTINUE_AFTER_VIDEO"
StateAskForDistressAfterVideo = "ASK_FOR_DISTRESS_AFTER_VIDEO"
StateGetDistressAfterVideo = "GET_DISTRESS_LEVEL_AFTER_VIDEO"
StateNextVideo = "NEXT_VIDEO"

async def start_isp(request_context: RequestContext, input: str):
    request_context.save_to_var(VariableSumDistressLevel, 0)
    request_context.save_to_var(VariableVideoIndex, 0)
    request_context.save_to_var(VariableWasDistressLevelIncreased, False)
States[StateStartISP] = State(chat_input=ChatInputNotWait, action_before=start_isp, conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableIspPath) == "1", output="startExercise1Danger", next_state=StateWaitForResponseBeforeVideo, condition_description="מוקד סכנה (1)"),
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableIspPath) == "2", output="startExercise2Accountability", next_state=StateWaitForResponseBeforeVideo, condition_description="מוקד אשמה (2)"),
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableIspPath) == "3", output="startExercise3Self", next_state=StateWaitForResponseBeforeVideo, condition_description="מוקד חוסר שליטה עצמי (3)"),
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableIspPath) == "4", output="startExercise4Future", next_state=StateWaitForResponseBeforeVideo, condition_description="מוקד חוסר שליטה עתיד (4)"),
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableIspPath) == "5", output="startExercise5Others", next_state=StateWaitForResponseBeforeVideo, condition_description="מוקד חוסר שליטה אחרים (5)"),
])

async def wait_for_response_before_video(request_context: RequestContext, input: str):
    if input == "לצאת":
        request_context.save_to_var(VariableIsUserExited, True)
States[StateWaitForResponseBeforeVideo] = State(chat_input=chat_input_multiple_options(["לצאת", "לתרגל עם סרטון"]), action_before=wait_for_response_before_video, conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: input == "לתרגל עם סרטון", output=None, next_state=StateShowVideo, condition_description="המשתמש\ת בחר\ה לצפות בסרטון"),
    ConditionedAction(condition=lambda request_context, input: input == "לצאת", output="genericExitText", next_state=StateExit, condition_description="המשתמש\ת בחר\ה לצפות בסרטון"),
    ConditionedAction(condition=None, output="wrongInputBeforeVideo", next_state=StateWaitForResponseBeforeVideo, condition_description=None),
])

States[StateShowVideo] = State(chat_input=ChatInputNotWait, conditioned_actions=[
    ConditionedAction(condition=None, output="videoUrl", next_state=StateAskForDistressAfterVideo, condition_description=None)
])

States[StateAskForDistressAfterVideo] = State(conditioned_actions=[
    ConditionedAction(condition=None, output="howMuchDistress", next_state=StateGetDistressAfterVideo, condition_description=None)
])

async def get_distress_level_after_video(request_context: RequestContext, input: str):
    distress = int(input)
    if not (0 <= distress <= 10):
        return None
    
    prev_distress = request_context.get_var(VariableDistressLevel)
    is_distress_increased = distress > prev_distress
    request_context.save_to_var(VariableDistressLevel, distress)
    request_context.save_to_var(VariablePrevDistressLevel, prev_distress)
    was_distress_level_increased_before = request_context.get_var(VariableWasDistressLevelIncreased)
    request_context.save_to_var(VariableWasDistressLevelIncreased, is_distress_increased)
    request_context.save_to_var(VariableSumDistressLevel, request_context.get_var(VariableSumDistressLevel) + distress)

    if was_distress_level_increased_before and is_distress_increased:
        request_context.save_to_var(VariableWasDistressLevelIncreasedTwice, True)
        return

    request_context.save_to_var(VariableWasDistressLevelIncreasedTwice, False)

    video_index = request_context.get_var(VariableVideoIndex)
    if video_index == 7:
        request_context.save_to_var(VariableIsUserExited, False)
States[StateGetDistressAfterVideo] = State(chat_input=chat_input_numeric(0, "0", 10, "10"), action_before=get_distress_level_after_video, conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: not (0 <= int(input) <= 10), output="wrongDistressLevel", next_state=StateGetDistressAfterVideo, condition_description="רמת המצוקה לא בין 0 ל-10"),
    ConditionedAction(condition=lambda request_context, input: (request_context.get_var(VariableWasDistressLevelIncreasedTwice) or request_context.get_var(VariableVideoIndex) == 7) and request_context.get_var(VariableIspPath) == "1", output=None, next_state=StateStartPositiveCognition, condition_description="שתי החרפות או אחרי וידאו שמיני, מוקד מצוקה סכנה"),
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableWasDistressLevelIncreasedTwice), output="exitAfterDistressIncreasedTwice", next_state=StateExit, condition_description="שתי החרפות, מוקד מצוקה אחר"),
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableVideoIndex) == 7, output="exitAfterDistressIncreasedTwice", next_state=StateChooseExitText, condition_description="אחרי וידאו שמיני"),
    ConditionedAction(condition=lambda request_context, input: int(input) < request_context.get_var(VariablePrevDistressLevel), output="shouldContinueAfterImprovement", next_state=StateGetIfToContinueAfterVideo, condition_description="הייתה הטבה"),
    ConditionedAction(condition=lambda request_context, input: int(input) == request_context.get_var(VariablePrevDistressLevel), output="shouldContinueAfterNoChange", next_state=StateGetIfToContinueAfterVideo, condition_description="רמת מצוקה נשארה זהה"),
    ConditionedAction(condition=None, output="shouldContinueAfterDistressIncreased", next_state=StateGetIfToContinueAfterVideo, condition_description=None),
])

async def get_if_to_continue_after_video(request_context: RequestContext, input: str):
    user_continued = input.strip() in ("fi", "כן", "טוב", "מוכן", "מוכנה", "בסדר", "בטח", "סבבה", "למה לא", "לך על זה", "לכי על זה", "קדימה", "אני על זה")
    request_context.save_to_var(VariableIsUserExited, not user_continued)
    if user_continued:
        video_index = request_context.get_var(VariableVideoIndex) + 1
        request_context.save_to_var(VariableVideoIndex, video_index)
States[StateGetIfToContinueAfterVideo] = State(chat_input=chat_input_multiple_options(["לא", "כן"]), action_before=get_if_to_continue_after_video, conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: not request_context.get_var(VariableIsUserExited), output=None, next_state=StateShowVideo, condition_description="המשתמש\ת הקליד\ה 'כן'"),
    ConditionedAction(condition=lambda request_context, input: not (input.strip() in ("kt", "לא", "פחות", "ממש לא", "אין מצב", "די", "מספיק")), output="wrongInputYesNo", next_state=StateGetIfToContinueAfterVideo, condition_description="קלט לא חוקי"),
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableIspPath) == "1", output=None, next_state=StateStartPositiveCognition, condition_description="המשתמש\ת הקליד\ה 'לא' ומוקד המצוקה סכנה"),
    ConditionedAction(condition=None, output=None, next_state=StateChooseExitText, condition_description=None),
])
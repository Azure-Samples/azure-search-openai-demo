from approaches.flow.shared_states import State, StateRedirectToOtherResources, StateStartISP, States
from approaches.requestcontext import RequestContext

StateShowFirstVideo = "SHOW_FIRST_VIDEO"

async def start_isp(request_context: RequestContext):
    isp_path = request_context.get_var("ispPath")
    prefixDict = {
        "1": "זו חוויה מאוד הגיונית שהרבה אנשים יכולים לחוות לאחר או במהלך אירוע קשה. התרגול שנעשה כעת יוכל להקל עליך.",
        "2": "מחשבות לגבי אחריות ואשמה נפוצות אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה כעת יוכל להקל עליך.",
        "3": "לעתים אחרי אירוע מאיים, שבו חווינו חוסר שליטה, התחושה הזו ממשיכה ללוות אותנו לזמן מה. התרגול שנעשה כעת יוכל להקל עליך.",
        "4": "מחשבות לגבי חוסר שליטה לגבי מצבים קשים עתידיים נפוצות אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה כעת יוכל להקל עליך.",
        "5": "זו תחושה טבעית אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה כעת יוכל להקל עליך. "
    }
    request_context.set_next_state(StateShowFirstVideo)
    return request_context.write_chat_message("""{prefix}
אציג לך כעת וידאו שילמד אותך לעשות תרגיל שיכול לעזור לך להשיג יותר שליטה ורוגע. צפה בו. נסה לא לעצום עיניים, לשמור על קשר עין עם המטפל/ת ופעל לפי ההנחיות בוידאו. """.format(prefix = prefixDict[isp_path]))
States[StateStartISP] = State(is_wait_for_user_input_before_state=False, run=start_isp)

async def show_first_video(request_context: RequestContext):
    isp_path = request_context.get_var("ispPath")
    videos = {
        "1": "http://youtube.com/watch?v=YE7VzlLtp-4",
        "2": "http://youtube.com/watch?v=YE7VzlLtp-4",
        "3": "http://youtube.com/watch?v=YE7VzlLtp-4",
        "4": "http://youtube.com/watch?v=YE7VzlLtp-4",
        "5": "http://youtube.com/watch?v=YE7VzlLtp-4",
    }
    return request_context.write_chat_message("צפה: {video}".format(video = videos[isp_path]))
States[StateShowFirstVideo] = State(run=show_first_video)

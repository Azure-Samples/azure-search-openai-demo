from approaches.videos import get_video_url
from approaches.flow.shared_states import VariableIspPath, VariablePatientName, VariableVideoIndex
from approaches.localization.glob import glob

contacts_text = """טלפון מרכז החוסן הארצי הטיפולי *5486 (פתוח בימים א-ה בין 8.00-20.00)
טלפון ער"ן  טלפון 1201 או  <a href="https://api.whatsapp.com/send/?phone=%2B972545903462&text&type=phone_number&app_absent=0">ווטסאפ</a> (השירות מוגש לכל מצוקה ובמגוון שפות, וניתן בצורה אנונימית ומיידית, 24 שעות ביממה בכל ימות השנה)"""

def how_much_distress(is_patient_male: bool):
    return """עד כמה {you} {annoyed} או חווה מצוקה כרגע (במספר)?
0  לא {annoyed} ולא חווה מצוקה כלל,
10 {annoyed} או חווה מצוקה ברמה חריפה""".format(
        can_you = "אתה יכול" if is_patient_male else "את יכולה",
        you = "אתה" if is_patient_male else "את",
        annoyed = "מוטרד" if is_patient_male else "מוטרדת")

def no_distress_on_start(is_patient_male: bool):
    return "אני {understand} שאינך חווה מצוקה כרגע. האם {want} לסיים את התהליך כעת?".format(understand = "מבין" if is_patient_male else "מבינה", want = "תרצה" if is_patient_male else "תרצי")

def wrong_distress_level(is_patient_male: bool):
    return "לא הבנתי את תשובתך. אנא {type} מספר בין 0 ל-10".format(type = "הקלד" if is_patient_male else "הקלידי")

def exit_no_distress(is_patient_male: bool):
    return """תודה שהתעניינת בכלי לסיוע עצמי במצבי מצוקה אחרי אירוע טראומטי. לעתים, גם אחרי שחווים אירוע מאיים או קשה, אין חווים תחושת קושי או מצוקה. אם {will_feel} בשלב כלשהו מצוקה {able} להשתמש בכלי זה או לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון
{contacts_text}""".format(
        will_feel = "תחוש" if is_patient_male else "תחושי",
        able = "תוכל" if is_patient_male else "תוכלי",
        contacts_text = contacts_text)

def choose_annoying_reason(is_patient_male: bool):
    return """מה הכי מטריד אותך כרגע?
1. אני {feel} <span style="font-weight: bolder">בסכנה/{threatened}</span>
2. אני {feel} <span style="font-weight: bolder">{guilty}</span> על משהו קשה שקרה
3. אני {feel} חוסר שליטה לגבי מה שקורה <span style="font-weight: bolder">עכשיו</span>
4. אני {feel} חוסר שליטה לגבי דברים שעלולים לקרות <span style="font-weight: bolder">בעתיד</span>
5. אני {concerned_and_feel} חוסר שליטה בנוגע <span style="font-weight: bolder">לאנשים שיקרים לי</span>""".format(
            feel = "מרגיש" if is_patient_male else "מרגישה",
            threatened = "מאויים" if is_patient_male else "מאויימת",
            guilty = "אשם" if is_patient_male else "אשמה",
            concerned_and_feel = "דואג וחש" if is_patient_male else "דואגת וחשה")

def choose_annoying_reason_with_distress(is_patient_male: bool, is_bot_male: bool, is_distress_high: bool):
    return "אני {understand} {that_you} חווה {some}מצוקה כרגע, בשביל זה אני כאן".format(
        understand = "מבין" if is_bot_male else "מבינה",
        that_you = "שאתה" if is_patient_male else "שאת",
        some = "" if is_distress_high else "מידה מסוימת של ") + """
""" + choose_annoying_reason(is_patient_male=is_patient_male)

def wrong_annoying_reason(is_patient_male: bool):
    return "לא הבנתי את תשובתך. אנא {type} מספר בין 1 ל-5".format(type = "הקלד" if is_patient_male else "הקלידי")

def start_exercise(text):
    full_text_without_name = """{text}. בדקות הקרובות אנחה אותך בתרגול.

אציג לך וידאו שילמד אותך לעשות תרגיל לייצוב מיידי.""".format(text = text)
    
    # Using similar logic for other variables requires updating FlowWriter logic to simulate this variable too
    return lambda request_context: request_context.get_var(VariablePatientName) + ", " + full_text_without_name

def wrong_input_before_video(is_patient_male: bool):
    return "לא הבנתי את תשובתך. אנא {type} לתרגל עם סרטון/לצאת".format(type = "הקלד" if is_patient_male else "הקלידי")

def get_video_message(request_context, is_patient_male: bool, is_bot_male: bool):
    # Using similar logic for other variables requires updating FlowWriter logic to simulate this variable too
    isp_path = request_context.get_var(VariableIspPath)
    video_index = request_context.get_var(VariableVideoIndex)
    video_index_to_show = 0 if video_index == 0 else ((video_index - 1) % 3 + 1)
    return [{"role": "vimeo", "content": get_video_url(isp_path, is_bot_male, is_patient_male, video_index_to_show)}]

def exit_after_distress_increased_twice(is_bot_male: bool):
    return """לאנשים שונים בזמנים שונים מתאימות התערבויות שונות. כיוון שאני {impressed} שקשה לך כעת אני {suggest} שנתקדם לקראת סיום התרגול.
לפני שנסיים אני רוצה להזכיר לך שהתגובות שחווית מאוד הגיוניות. הרבה פעמים אחרי שחווים אירוע מאיים או קשה או במצבים שחוששים מאירועים כאלה חווים קושי או מצוקה. אני רוצה לציין בפניך את העובדה שיש לך אפשרות לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון:
{contacts_text}""".format(
        impressed = "מתרשם" if is_bot_male else "מתרשמת",
        suggest = "מציע" if is_bot_male else "מציעה",
        contacts_text = contacts_text)

def wrong_has_improvement(is_patient_male: bool):
    return "לא הבנתי את תשובתך. אנא {type} ללא שיפור/שיפור מועט/שיפור גדול".format(type = "הקלד" if is_patient_male else "הקלידי")

def exit_by_improvement(is_patient_male: bool, is_bot_male: bool, improvement_description: str):
    return """לפני שנסיים אני רוצה להזכיר לך שהתגובות שחווית מאוד הגיוניות. הרבה פעמים אחרי שחווים אירוע מאיים או קשה או במצבים שחוששים מאירועים כאלה חווים קושי או מצוקה. אני רוצה לציין בפניך את העובדה {improvement_description} אם {will_feel} שוב מצוקה. בנוסף אני רוצה לציין כי {you_might} לחוות בהמשך כל מיני קשיים, שהם טבעיים ונורמליים כמו תמונות של מה שקרה או {that_you_afraid} שיקרה, קושי בשינה, ומספר רגשות כמו מצוקה, פחד או כעס. אם {experience} אותם, מומלץ לך להשתמש בתרגול שעשינו.
אם {you_notice} לב שהתגובות האלה לא פוחתות, או נמשכות יותר מ 2-3 ימים, אני {encourage} אותך לפנות לאחד מהגופים הבאים, שיוכלו לעזור לך להתמודד עם התגובות האלו:
{contacts_text}
אני מקווה שסייעתי לך {wish} לך הקלה משמעותית נוספת במצבך""".format(
        improvement_description = improvement_description,
        will_feel = "תחוש" if is_patient_male else "תחושי",
        you_might = "אתה עלול" if is_patient_male else "את עלולה",
        that_you_afraid = "שאתה חושש" if is_patient_male else "שאת חוששת",
        experience = "תחווה" if is_patient_male else "תחווי",
        you_notice = "אתה שם" if is_patient_male else "את שמה",
        encourage = "מעודד" if is_bot_male else "מעודדת",
        contacts_text = contacts_text,
        wish = "ומאחל" if is_bot_male else "ומאחלת")

exit_after_distress_increased = """לפני שנסיים אני רוצה להזכיר לך שהתגובות שחווית מאוד הגיוניות. הרבה פעמים אחרי שחווים אירוע מאיים או קשה או במצבים שחוששים מאירועים כאלה חווים קושי או מצוקה. אני רוצה לציין בפניך את העובדה שיש לך אפשרות לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון:
{contacts_text}""".format(contacts_text = contacts_text)

def exit_after_improvement(is_patient_male: bool, is_bot_male: bool):
    return exit_by_improvement(is_patient_male=is_patient_male, is_bot_male=is_bot_male, improvement_description="שתיארת שיפור בין תחילת התרגול לסיומו ולעודד אותך לעשות שימוש בתרגול שעשינו")

def exit_no_clear_improvement(is_patient_male: bool, is_bot_male: bool):
    return """סיימנו את התרגול. אני מקווה שתיתרם ממנו. לעיתים השיפור מופיע בהמשך, לאחר שעות או ימים מתום התרגול.    
לפני שנסיים אני רוצה להזכיר לך שהתגובות שחווית מאוד הגיוניות, ושלאנשים שונים בזמנים שונים מתאימות התערבויות שונות. הרבה פעמים אחרי שחווים אירוע מאיים או קשה או במצבים שחוששים מאירועים כאלה חווים קושי או מצוקה, ויש  לך אפשרות לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון:
{contacts_text}"""

def should_continue_after_improvement(is_patient_male: bool, is_bot_male: bool):
    return """אני {happy} {that_you} חווה שיפור, ייתכן שיפור נוסף עם התרגול. האם {want} להמשיך?""".format(
        happy = "שמח" if is_bot_male else "שמחה", that_you = "שאתה" if is_patient_male else "שאת", want = "תרצה" if is_patient_male else "תרצי")

def should_continue_after_no_change(is_patient_male: bool):
    return """חלק מהאנשים חווים שיפור אחרי תרגול נוסף. האם {want} להמשיך לתרגל?""".format(want = "תרצה" if is_patient_male else "תרצי")

def should_continue_after_distress_increased(is_patient_male: bool):
    return """אני מבין שקשה לך. "האם {you_ready} להמשיך לתרגל?""".format(you_ready = "אתה מוכן" if is_patient_male else "את מוכנה")

def had_improvement(is_patient_male: bool):
    return """באיזו מידה {you_feel} שיפור ביכולת שלך להתמודד עם החוויה? ללא שיפור / שיפור מועט / שיפור קל / שיפור בינוני / שיפור גדול""".format(you_feel = "אתה מרגיש" if is_patient_male else "את מרגישה")

def is_connected_to_current(is_patient_male: bool):
    return """

עד כמה {you_connect} למה שקורה עכשיו, {and_feel} שגם אם קרה אירוע קשה, הוא נגמר?

כלל לא / במידה מועטה / במידה מתונה / במידה רבה / במידה רבה מאד""".format(you_connect = "אתה מחובר" if is_patient_male else "את מחוברת", and_feel = "ומרגיש" if is_patient_male else "ומרגישה")

def wrong_is_connected_to_current(is_patient_male: bool):
    return "לא הבנתי את תשובתך. אנא {type} כלל לא/במידה מועטה/במידה מתונה/במידה רבה/במידה רבה מאד".format(type = "הקלד" if is_patient_male else "הקלידי")

def is_connected_to_current_after_improvement(is_patient_male: bool, is_bot_male: bool):
    return """אני {happy} לראות {that_you_succeeding} לעזור לעצמך באמצעות התרגול.{is_connected}""".format(
        happy = "שמח" if is_bot_male else "שמחה",
        that_you_succeeding = "שאתה מצליח" if is_patient_male else "שאת מצליחה",
        is_connected = is_connected_to_current(is_patient_male))

def is_connected_to_current_after_no_improvement(is_patient_male: bool, is_bot_male: bool):
    return "אני {understand}, עם זאת חשוב לציין שחלק מהאנשים לא חווים שיפור מיד בסוף התרגול אלא מאוחר יותר, ויתכן {feel} שיפור בהמשך.{is_connected}".format(
        understand = "מבין" if is_bot_male else "מבינה",
        feel = "שתחוש" if is_patient_male else "שתחושי",
        is_connected = is_connected_to_current(is_patient_male))

def exit_after_fail_to_connect_to_current(is_bot_male: bool):
    return "אני {understand}, ורוצה להזכיר לך שלפעמים אחרי אירוע קשה לוקח זמן להתחבר שוב להווה. יתכן שהתהליך הזה יתרחש בהמשך.".format(
        understand = "מבין" if is_bot_male else "מבינה",
        that_you_here = "שאתה נמצא" if is_bot_male else "שאת נמצאת"
    )

def exit_after_succeed_to_connect_to_current(is_patient_male: bool, is_bot_male: bool):
    return "אני {happy} לראות שלמרות מה שחווית {that_you_succeeding} להתחבר להווה.".format(
        happy = "שמח" if is_bot_male else "שמחה",
        that_you_succeeding = "שאתה מצליח" if is_patient_male else "שאת מצליחה")

def exit_after_distress_increased_and_fail_to_connect_to_current(is_patient_male: bool, is_bot_male: bool):
    return exit_after_fail_to_connect_to_current(is_bot_male) + """
""" + exit_after_distress_increased

def exit_after_distress_increased_and_succeed_to_connect_to_current(is_patient_male: bool, is_bot_male: bool):
    return exit_after_succeed_to_connect_to_current(is_patient_male, is_bot_male) + """
""" + exit_after_distress_increased

def exit_after_improvement_and_fail_to_connect_to_current(is_patient_male: bool, is_bot_male: bool):
    return exit_after_fail_to_connect_to_current(is_bot_male) + """
""" + exit_after_improvement(is_patient_male, is_bot_male)

def exit_after_improvement_and_succeed_to_connect_to_current(is_patient_male: bool, is_bot_male: bool):
    return exit_after_succeed_to_connect_to_current(is_patient_male, is_bot_male) + """
""" + exit_after_improvement(is_patient_male, is_bot_male)

def exit_after_no_clear_improvement_and_succeed_to_connect_to_current(is_patient_male: bool, is_bot_male: bool):
    return exit_after_succeed_to_connect_to_current(is_patient_male, is_bot_male) + """
""" + exit_no_clear_improvement(is_patient_male, is_bot_male)

def exit_after_no_clear_improvement_and_fail_to_connect_to_current(is_patient_male: bool, is_bot_male: bool):
    return exit_after_fail_to_connect_to_current(is_bot_male) + """
""" + exit_no_clear_improvement(is_patient_male, is_bot_male)


he = {
    "id": "he",
    "parent": glob["id"],
    "mustUserId": "כניסה ללא זיהוי משתמש לא אפשרית כרגע. נא לפנות לצוות לקבלת קישור",
    "authFailed": "אירעה שגיאה בזיהוי. ייתכן כי הקישור לא תקין. נא לפנות לצוות לקבלת קישור חדש",
    "participationDone": """השתתפותך כבר הסתיימה, תודה! יש לך אפשרות לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון
{contacts_text}""".format(contacts_text = contacts_text),
    "participationCutInThePast": "השתתפותך נקטעה בעבר באופן לא צפוי, נא לפנות לצוות לקבלת קישור חדש",
    "statusUnexpected": "אירעה שגיאה. ייתכן כי הקישור לא תקין. נא לפנות לצוות לקבלת קישור חדש",
    "whatIsYourAge": "מה גילך?",
    "chooseBotGender": "לתהליך הנוכחי, מה תעדיפ/י?",
    "ageLessThan18": """תודה שהתעניינת בכלי לסיוע עצמי במצבי מצוקה אחרי אירוע טראומטי. כרגע המערכת פתוחה לאנשים מעל גיל 18. היות שהרבה פעמים אחרי שחווים אירוע מאיים או קשה, או במצבים שחוששים מאירועים כאלה, חווים קושי או מצוקה, אם אתה חווה מצוקה, אפשר לפנות לסיוע נפשי ולקבל כלים להתמודדות בגופים שונים כגון
{contacts_text}""".format(contacts_text = contacts_text),
    "illegalAge": "הגיל שהכנסת אינו חוקי, יש להכניס מספר בלבד",
    "botGenderInputWrong": "לא הבנתי את תשובתך. אנא הקלד/י מטפל או מטפלת?",
    "whatIsYourName": "מה שמך?",
    "choosePatientGender": "איך לפנות אליך/אלייך?",
    "patientGenderInputWrong": "לא הבנתי את תשובתך. אנא הקלד/י נקבה/זכר?",
    "startExercise1Danger": start_exercise("זו חוויה מאוד הגיונית שהרבה אנשים חווים. התרגול שנעשה כעת יוכל להקל עליך, הוא ידוע כתרגול שעזר לאנשים רבים"),
    "startExercise2Accountability": start_exercise("מחשבות לגבי אחריות ואשמה נפוצות אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה יוכל להקל עליך"),
    "startExercise3Self": start_exercise("לעתים לאחר אירוע מאיים, שבו חווינו חוסר שליטה, התחושה הזו ממשיכה ללוות אותנו לזמן מה. התרגול שנעשה כעת יוכל להקל עליך"),
    "startExercise4Future": start_exercise("מחשבות לגבי חוסר שליטה לגבי מצבים קשים עתידיים נפוצות אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה כעת יוכל להקל עליך"),
    "startExercise5Others": start_exercise("זו תחושה טבעית אחרי חשיפה לאירועים קשים ומאיימים. התרגול שנעשה כעת יוכל להקל עליך"),
    "genericExitText": """תודה שהתעניינת בכלי לסיוע עצמי במצבי מצוקה. 
הרבה פעמים אחרי שחווים אירוע מאיים או קשה, או במצבים שחוששים מאירועים כאלה, חווים קושי או מצוקה. יש לך אפשרות לפנות לסיוע נפשי ולקבל כלים אחרים בגופים שונים כגון
{contacts_text}""".format(contacts_text = contacts_text),
    "exitTextAfterDistressIncreased": exit_after_distress_increased,
}
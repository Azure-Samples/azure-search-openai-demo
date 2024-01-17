import { Checkbox } from '@fluentui/react';
import styles from './TermsOfService.module.css';

import React, { useState } from 'react';

interface TermsOfServiceProps {
    onButtonClicked: () => void;
}

const TermsOfService: React.FC<TermsOfServiceProps> = ({ onButtonClicked }) => {
    const [isChecked, setIsChecked] = useState(false);

    function onCheckboxChange(ev?: React.FormEvent<HTMLElement | HTMLInputElement>, isChecked?: boolean) {
        setIsChecked(isChecked ?? false);
    }

    return (
        <div className={styles.rootContainer}>
            <div className={styles.container}>
                <div className={styles.textspace}>
                    <p className={styles.label}>אנא אשר את תנאי השימוש שלנו:</p>
                    <p className={styles.content}>
                        השימוש בכלי זה נמצא כעת בשלב מחקר ופיתוח בקרב חוקרי אקדמיה. בשלב הזה הוא נועד למבוגרים מעל גיל 18, דוברי עברית,
                        שאינם מאובחנים עם מחלה פסיכוטית ושאינם מתמודדים חשים מסוכנים לעצמם או לאחרים. אם אתה מתמודד עם מחשבות אובדניות
                        או חושש שתפגע בעצמך או באחר, נא פנה לאחד מגורמי התמיכה הבאים:
                        <br />
                        המידע והתרגולים שמוצעים כאן הם למידע כללי בלבד ולא מיועדים לטיפול רפואי או כל טיפול של מקצועות בריאות אחרים.
                        המידע אינו מחליף ייעוץ מקצועי רפואי. השימוש במידע ובתרגולים כאן הוא באחריות המשתמש בלבד. תוכן בן השיח הדיגיטלי
                        הוא לא תחליף לייעוץ, אבחון או טיפול רפואיים. האחריות על השימוש בתומך הדיגיטלי היא על המשתמש/ת בלבד.
                    </p>
                    <Checkbox
                        styles={{ checkbox: { borderRadius: '100%' } }} label="אני יודע/ת שמידע שנאסף כאן נשמר על מנת לחקור את התחום של יעילות כלים דיגיטליים אחרי אירוע טראומטי לצמצום מתחים וכי שום מידע אישי מזהה לא נאסף."
                        onChange={onCheckboxChange}
                    />
                    <p className={styles.content}>ניתן ליצור קשר באימייל:
                        <a href="mailto:amirt2@tauex.tau.ac.il" rel="noopener noreferrer" target="_blank">
                            <span className={styles.emailLink}>amirt2@tauex.tau.ac.il</span>
                        </a>
                    </p>
                </div>
                <div className={styles.buttonpadding} />
                <div className={styles.buttonscontainer}>
                    <button className={styles.exitbutton}>ליציאה</button>
                    <button className={styles.confirmbutton} disabled={!isChecked} onClick={onButtonClicked} >לאישור והמשך</button>
                </div>
            </div>
        </div>
    );
};

export default TermsOfService;

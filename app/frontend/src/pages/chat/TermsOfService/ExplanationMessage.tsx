import React from 'react';
import styles from './ExplanationMessage.module.css';

interface ExplanationMessageProps {
    onButtonClicked: () => void;
}

const ExplanationMessage: React.FC<ExplanationMessageProps> = ({ onButtonClicked }) => {
    return (
        <div className={styles.rootContainer}>
            <div className={styles.container}>
                <p className={styles.ISP}>
                    ברוך/ה הבא/ה לכלי סיוע עצמי במצבי מצוקה אחרי אירוע טראומטי. <br />
                    הכלים והידע שכלי זה עושה בהם שימוש מבוססים על פרוטוקול ISP (Immediate Support Protocol) שנמצא יעיל מחקרית לצמצום
                    רמות חרדה אחרי אירוע טראומטי. הכלי הוא דיגיטלי ואיננו כולל מעורבות אנושית בפעילותו השוטפת. הוא כולל טכנולוגיה של
                    בינה מלאכותית יוצרת כדי לשפר את חווית המשתמש בו, אך בעיקרו נועד להנגיש באופן מסודר ומובנה את הפרוטוקול לתמיכה
                    מיידית לשימוש עצמי.
                </p>
                <div className={styles.buttonpadding} />
                <div className={styles.buttonWrapper}>
                    <button className={styles.gototosbutton} onClick={() => onButtonClicked()}>לאישור תנאי השימוש</button>
                </div>
            </div>
        </div>
    );
};

export default ExplanationMessage;

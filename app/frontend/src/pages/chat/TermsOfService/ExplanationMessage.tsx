import React from "react";
import styles from "./ExplanationMessage.module.css";

interface ExplanationMessageProps {
    onButtonClicked: () => void;
}

const ExplanationMessage: React.FC<ExplanationMessageProps> = ({ onButtonClicked }) => {
    return (
        <div className={styles.rootContainer}>
            <div className={styles.container}>
                <p className={styles.ISP}>
                    ברוך/ה הבא/ה לכלי סיוע עצמי במצבי מצוקה אחרי אירוע טראומטי. <br />
                    כלי זה עושה שימוש בשיטת <span dir="ltr">ISP (Immediate Stabilization Procedure®)</span> שנמצאה יעילה מחקרית לצמצום רמות חרדה אחרי אירוע
                    טראומטי. הכלי דיגיטלי, ללא מעורבות אנושית בפעילותו השוטפת. הוא כולל טכנולוגיה שנועדה לשפר את חווית המשתמש בו, ולהנגיש באופן מסודר ומובנה את
                    השיטה לשימוש עצמי.
                </p>
                <div className={styles.buttonpadding} />
                <div className={styles.buttonWrapper}>
                    <button className={styles.gototosbutton} onClick={() => onButtonClicked()}>
                        לאישור תנאי השימוש
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ExplanationMessage;

import React from 'react';
import styles from './ChatHeader.module.css';
import introImage from "../../assets/intro.png";

const ChatHeader: React.FC = () => {
    return (
        <div>
            <div className={styles.chatHeader}>חרבות ברזל - תמיכה והכוונה רגשית</div>
            <div className={styles.invisibleChatHeader}> </div>
            <div className={styles.chatIntroContainer}>
                <div className={styles.chatIntroImageContainer}>
                    <div className={styles.chatIntroImageViewport}>
                        <img src={introImage} className={styles.chatIntroImage} />
                    </div>
                </div>
                <div className={styles.chatIntroText}>אנחנו כאן עבורך</div>
            </div>
        </div>
    );
};

export default ChatHeader;

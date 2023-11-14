import styles from "./ChatHistory.module.css";
import {useState} from "react";
import {ChatHistorySessionModal} from "../chathistorySessionModal/ChatHistorySessionModal"
import { Container } from 'react-bootstrap';

const ChatHistory = () => {
    type SessionType = {
        name: string,
        creationDate: string,
        lastModificationDate: string
    };

    const [sessions, setSessions] = useState<SessionType[]>([]);
    const [showModal, setShowModal] = useState<boolean>(false);

    const handleShowModal = () => {
        setShowModal(true);
    };

    const handleCloseModal = () => {
        setShowModal(false);
    };

    const handleCreateSession = (sessionName: string) => {
        const newSession = {
            name: sessionName,
            creationDate: new Date().toDateString(),
            lastModificationDate: new Date().toDateString()
        }
        setSessions([...sessions, newSession])
        console.log(`Session created with name: ${sessionName}`);
    };

    const handleClickOnChatSession = (session: SessionType) => {
        console.log("success!")
        window.location.href = `/${session.name}`;
    };

    return (
        <>
            <div className={`content ${showModal ? styles.blurred : ''}`} >
                <div className={styles.chatHistory}>
                    {sessions.map((session, index) => (
                        <button key={index} onClick={handleClickOnChatSession.bind(this, session)}
                                className={styles.chatSessions} disabled={showModal}>
                            <text style={{fontSize: "40px", alignSelf: "center"}}> {session.name} </text>
                        </button>
                    ))}
                    <button type="submit"
                            className={styles.chatSessionButton}
                            onClick={handleShowModal}>
                        <span className={styles.buttonContent}> + </span>
                    </button>

                </div>
            </div>
            <div>
                <ChatHistorySessionModal
                    show={showModal}
                    handleClose={handleCloseModal}
                    handleCreateSession={handleCreateSession}
                />
            </div>
        </>
    );
};

export default ChatHistory;

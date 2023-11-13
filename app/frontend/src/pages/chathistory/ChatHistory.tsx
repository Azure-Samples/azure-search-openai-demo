import styles from "./ChatHistory.module.css";
import {useState} from "react";
import {ChatHistorySessionModal} from "../chathistorySessionModal/ChatHistorySessionModal"
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
        <div className={styles.container}>
            <div className={styles.commandsContainer}>
                {sessions.map((session, index) => (
                    <button key={index} onClick={handleClickOnChatSession.bind(this, session)}
                            className='chat-sessions'>
                        <text style={{fontSize: "40px", alignSelf: "center"}}> {session.name} </text>
                    </button>
                ))}
                <button type="submit"
                        className="chat-session-button"
                        onClick={handleShowModal}>
                    <span className="button-content">+</span>
                </button>

                <ChatHistorySessionModal
                    // className="modal"
                    show={showModal}
                    handleClose={handleCloseModal}
                    handleCreateSession={handleCreateSession}
                />
            </div>
        </div>
    );
};

export default ChatHistory;

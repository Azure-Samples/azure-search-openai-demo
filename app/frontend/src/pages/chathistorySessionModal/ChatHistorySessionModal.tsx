import React, {ChangeEvent, useState} from 'react';
import { Modal, Button, Form } from 'react-bootstrap';
import styles from './ChatHistorySessionModal.module.css';
interface SessionModalProps {
    show: boolean;
    handleClose: () => void;
    handleCreateSession: (input: string) => void;
}
export function ChatHistorySessionModal(props: SessionModalProps) {
    const show = props.show;
    const handleClose = props.handleClose;
    const handleCreateSession = props.handleCreateSession;
    const [sessionName, setSessionName] = useState<string>('');

    const handleSessionNameChange = (e: ChangeEvent<HTMLInputElement>) => {
        setSessionName(e.target.value);
    };

    const customStyles = {
        content: {
            top: '20%',
            left: '50%', // Center the modal horizontally
            transform: 'translate(40vw, -50vh)', // Center the modal vertically
            backgroundColor: 'white',
            width: '300px',
            maxHeight: '80%',
            border: '4px solid #000000',
            padding: '20px', // Add padding to separate content from the border
        },
    };

    const handleCreateClick = () => {
        if (sessionName.trim() === '') {
            alert('Please enter a valid session name.');
        } else {
            handleCreateSession(sessionName);
            setSessionName("")
            handleClose();
        }
    };

    return (
        // <div className={styles.modal} style={customStyles.content}>
        <Modal show={show} onHide={handleClose} style={customStyles.content} >
            <Modal.Body>
                <Form.Group controlId="sessionName">
                    <Form.Label> Session Name </Form.Label>
                    <Form.Control
                        type="text"
                        placeholder="Enter session name"
                        value={sessionName}
                        onChange={handleSessionNameChange}
                    />
                </Form.Group>
            </Modal.Body>
            <p>    </p>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose}>
                    Close
                </Button>
                <Button style={{"marginLeft": "10px"}} variant="primary" onClick={handleCreateClick}>
                    Create
                </Button>
            </Modal.Footer>
        </Modal>
        // </div>
    );
}
